"""ATLAS Ontoloji Yoneticisi modulu.

Sema tanimlama, sinif hiyerarsisi, ozellik kisitlamalari,
dogrulama kurallari ve sema evrimi.
"""

import logging
from typing import Any

from app.models.knowledge import (
    EntityType,
    OntologyClass,
    PropertyType,
)

logger = logging.getLogger(__name__)


class OntologyManager:
    """Ontoloji yoneticisi.

    Bilgi grafi icin sema tanimlama, sinif hiyerarsisi,
    ozellik kisitlamalari ve dogrulama saglar.

    Attributes:
        _classes: Ontoloji siniflari (id -> OntologyClass).
        _name_index: Ad -> sinif ID indeksi.
        _entity_type_map: EntityType -> sinif ID eslesmesi.
        _validation_rules: Dogrulama kurallari.
    """

    def __init__(self) -> None:
        """Ontoloji yoneticisini baslatir."""
        self._classes: dict[str, OntologyClass] = {}
        self._name_index: dict[str, str] = {}
        self._entity_type_map: dict[str, str] = {}
        self._validation_rules: list[dict[str, Any]] = []
        self._version: int = 0

        logger.info("OntologyManager baslatildi")

    def define_class(
        self,
        name: str,
        parent_name: str | None = None,
        properties: dict[str, PropertyType] | None = None,
        constraints: dict[str, Any] | None = None,
        description: str = "",
    ) -> OntologyClass:
        """Ontoloji sinifi tanimlar.

        Args:
            name: Sinif adi.
            parent_name: Ust sinif adi (None ise kok sinif).
            properties: Ozellik tanimlari.
            constraints: Kisitlamalar.
            description: Aciklama.

        Returns:
            Olusturulan OntologyClass.
        """
        parent_id = None
        if parent_name:
            parent_id = self._name_index.get(parent_name.lower())

        ont_class = OntologyClass(
            name=name,
            parent_id=parent_id,
            properties=properties or {},
            constraints=constraints or {},
            description=description,
        )
        self._classes[ont_class.id] = ont_class
        self._name_index[name.lower()] = ont_class.id

        logger.info("Ontoloji sinifi tanimlandi: %s", name)
        return ont_class

    def get_class(self, name: str) -> OntologyClass | None:
        """Ada gore sinif getirir.

        Args:
            name: Sinif adi.

        Returns:
            OntologyClass veya None.
        """
        class_id = self._name_index.get(name.lower())
        if class_id:
            return self._classes.get(class_id)
        return None

    def get_class_by_id(self, class_id: str) -> OntologyClass | None:
        """ID'ye gore sinif getirir."""
        return self._classes.get(class_id)

    def get_hierarchy(self, name: str) -> list[str]:
        """Sinif hiyerarsisini getirir (kok -> yaprak).

        Args:
            name: Sinif adi.

        Returns:
            Hiyerarsi listesi (ust siniflardan alta).
        """
        hierarchy: list[str] = []
        class_id = self._name_index.get(name.lower())

        visited: set[str] = set()
        while class_id and class_id not in visited:
            visited.add(class_id)
            ont_class = self._classes.get(class_id)
            if not ont_class:
                break
            hierarchy.append(ont_class.name)
            class_id = ont_class.parent_id

        hierarchy.reverse()
        return hierarchy

    def get_children(self, name: str) -> list[OntologyClass]:
        """Alt siniflari getirir.

        Args:
            name: Ust sinif adi.

        Returns:
            Alt sinif listesi.
        """
        parent_id = self._name_index.get(name.lower())
        if not parent_id:
            return []

        return [c for c in self._classes.values() if c.parent_id == parent_id]

    def add_property(self, class_name: str, prop_name: str, prop_type: PropertyType) -> bool:
        """Sinifa ozellik ekler.

        Args:
            class_name: Sinif adi.
            prop_name: Ozellik adi.
            prop_type: Ozellik tipi.

        Returns:
            Basarili mi.
        """
        ont_class = self.get_class(class_name)
        if not ont_class:
            return False

        ont_class.properties[prop_name] = prop_type
        return True

    def add_constraint(self, class_name: str, constraint_name: str, constraint: Any) -> bool:
        """Sinifa kisitlama ekler.

        Args:
            class_name: Sinif adi.
            constraint_name: Kisitlama adi.
            constraint: Kisitlama degeri.

        Returns:
            Basarili mi.
        """
        ont_class = self.get_class(class_name)
        if not ont_class:
            return False

        ont_class.constraints[constraint_name] = constraint
        return True

    def get_all_properties(self, class_name: str) -> dict[str, PropertyType]:
        """Sinifin tum ozelliklerini getirir (miras dahil).

        Args:
            class_name: Sinif adi.

        Returns:
            Ozellik adi -> tip eslesmesi.
        """
        all_props: dict[str, PropertyType] = {}
        hierarchy = self.get_hierarchy(class_name)

        # Hiyerarsi boyunca ozellikleri topla (ust -> alt)
        for cls_name in hierarchy:
            ont_class = self.get_class(cls_name)
            if ont_class:
                all_props.update(ont_class.properties)

        return all_props

    def validate_entity(self, entity_type: str, attributes: dict[str, Any]) -> list[str]:
        """Varligi ontoloji kurallarinaa gore dogrular.

        Args:
            entity_type: Varlik tipi.
            attributes: Varlik ozellikleri.

        Returns:
            Hata mesajlari listesi (bos ise gecerli).
        """
        errors: list[str] = []

        # Ozel dogrulama kurallari
        for rule in self._validation_rules:
            if rule.get("entity_type") and rule["entity_type"] != entity_type:
                continue

            required = rule.get("required_properties", [])
            for prop in required:
                if prop not in attributes:
                    errors.append(f"Zorunlu ozellik eksik: {prop}")

            # Tip kontrolu
            type_checks = rule.get("type_checks", {})
            for prop, expected_type in type_checks.items():
                if prop in attributes:
                    value = attributes[prop]
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"{prop} string olmali")
                    elif expected_type == "integer" and not isinstance(value, int):
                        errors.append(f"{prop} integer olmali")
                    elif expected_type == "float" and not isinstance(value, (int, float)):
                        errors.append(f"{prop} float olmali")

            # Deger araligi
            ranges = rule.get("ranges", {})
            for prop, (min_val, max_val) in ranges.items():
                if prop in attributes:
                    val = attributes[prop]
                    if isinstance(val, (int, float)):
                        if val < min_val or val > max_val:
                            errors.append(f"{prop} {min_val}-{max_val} araliginda olmali")

        return errors

    def add_validation_rule(self, rule: dict[str, Any]) -> None:
        """Dogrulama kurali ekler.

        Args:
            rule: Kural tanimlari (entity_type, required_properties, type_checks, ranges).
        """
        self._validation_rules.append(rule)
        logger.info("Dogrulama kurali eklendi")

    def map_entity_type(self, entity_type: EntityType, class_name: str) -> bool:
        """EntityType'i ontoloji sinifina esler.

        Args:
            entity_type: Varlik tipi enum.
            class_name: Ontoloji sinif adi.

        Returns:
            Basarili mi.
        """
        if not self.get_class(class_name):
            return False

        self._entity_type_map[entity_type.value] = class_name
        return True

    def evolve_schema(self, changes: list[dict[str, Any]]) -> int:
        """Semayi evrimlestirir.

        Args:
            changes: Degisiklik listesi (action, target, data).

        Returns:
            Uygulanan degisiklik sayisi.
        """
        applied = 0

        for change in changes:
            action = change.get("action")
            target = change.get("target", "")

            if action == "add_class":
                self.define_class(
                    name=target,
                    parent_name=change.get("parent"),
                    properties=change.get("properties"),
                    description=change.get("description", ""),
                )
                applied += 1

            elif action == "add_property":
                prop_name = change.get("property", "")
                prop_type = change.get("type", PropertyType.STRING)
                if isinstance(prop_type, str):
                    prop_type = PropertyType(prop_type)
                if self.add_property(target, prop_name, prop_type):
                    applied += 1

            elif action == "remove_property":
                ont_class = self.get_class(target)
                if ont_class:
                    prop_name = change.get("property", "")
                    ont_class.properties.pop(prop_name, None)
                    applied += 1

            elif action == "rename_class":
                ont_class = self.get_class(target)
                if ont_class:
                    new_name = change.get("new_name", "")
                    old_lower = target.lower()
                    self._name_index.pop(old_lower, None)
                    ont_class.name = new_name
                    self._name_index[new_name.lower()] = ont_class.id
                    applied += 1

        if applied > 0:
            self._version += 1
            logger.info("Sema evrimi: %d degisiklik (v%d)", applied, self._version)

        return applied

    def export_schema(self) -> dict[str, Any]:
        """Semayi disari aktarir.

        Returns:
            Sema sozlugu.
        """
        return {
            "version": self._version,
            "classes": [
                {
                    "id": c.id,
                    "name": c.name,
                    "parent_id": c.parent_id,
                    "properties": {k: v.value for k, v in c.properties.items()},
                    "constraints": c.constraints,
                    "description": c.description,
                }
                for c in self._classes.values()
            ],
            "entity_type_map": self._entity_type_map,
            "validation_rules": self._validation_rules,
        }

    @property
    def class_count(self) -> int:
        """Sinif sayisi."""
        return len(self._classes)

    @property
    def version(self) -> int:
        """Sema versiyonu."""
        return self._version

    @property
    def classes(self) -> list[OntologyClass]:
        """Tum siniflar."""
        return list(self._classes.values())
