"""ATLAS Kod Planlayici modulu.

Dosya yapisi planlama, modul bagimliliklari, arayuz tasarimi,
test stratejisi ve uygulama sirasi belirleme.
"""

import logging
from typing import Any

from app.models.nlp_engine import (
    CodePlan,
    PlannedFile,
    TechnicalSpec,
)

logger = logging.getLogger(__name__)


class CodePlanner:
    """Kod planlayici.

    Teknik spesifikasyonlardan dosya yapisi, modul
    bagimliliklari, arayuz tanimlari, test stratejisi
    ve uygulama sirasi planlar.

    Attributes:
        _plans: Kod planlari (id -> CodePlan).
    """

    def __init__(self) -> None:
        """Kod planlayiciyi baslatir."""
        self._plans: dict[str, CodePlan] = {}

        logger.info("CodePlanner baslatildi")

    def plan(self, title: str, spec: TechnicalSpec | None = None, modules: list[str] | None = None) -> CodePlan:
        """Kod plani olusturur.

        Spesifikasyondan veya modul listesinden dosya yapisi,
        bagimliliklar ve uygulama sirasi planlar.

        Args:
            title: Plan basligi.
            spec: Teknik spesifikasyon.
            modules: Modul listesi (spec yoksa kullanilir).

        Returns:
            CodePlan nesnesi.
        """
        files: list[PlannedFile] = []

        if spec:
            files = self._plan_from_spec(spec)
        elif modules:
            files = self._plan_from_modules(modules)

        # Arayuzleri belirle
        interfaces = self._design_interfaces(files)

        # Test stratejisi
        test_strategy = self._plan_test_strategy(files)

        # Uygulama sirasi
        impl_order = self._determine_implementation_order(files)

        plan = CodePlan(
            title=title,
            files=files,
            interfaces=interfaces,
            test_strategy=test_strategy,
            implementation_order=impl_order,
        )
        self._plans[plan.id] = plan

        logger.info("Kod plani olusturuldu: %s (%d dosya)", title, len(files))
        return plan

    def plan_file_structure(self, base_path: str, components: list[dict[str, str]]) -> list[PlannedFile]:
        """Dosya yapisi planlar.

        Args:
            base_path: Temel dizin yolu.
            components: Bilesenlerin listesi (name, purpose).

        Returns:
            Planlanmis dosyalar listesi.
        """
        files: list[PlannedFile] = []

        # __init__.py
        files.append(PlannedFile(
            path=f"{base_path}/__init__.py",
            purpose="Paket baslatma ve disa aktarim",
            estimated_lines=20,
            priority=1,
        ))

        for i, comp in enumerate(components):
            name = comp.get("name", f"component_{i}")
            purpose = comp.get("purpose", "")
            files.append(PlannedFile(
                path=f"{base_path}/{name}.py",
                purpose=purpose,
                estimated_lines=100,
                priority=i + 2,
            ))

        return files

    def identify_dependencies(self, files: list[PlannedFile]) -> dict[str, list[str]]:
        """Dosyalar arasi bagimliliklari tespit eder.

        __init__.py tum modullere bagimli, test dosyalari
        kaynak modullerine bagimli.

        Args:
            files: Planlanmis dosyalar.

        Returns:
            Bagimlilik haritasi (dosya yolu -> bagimli dosya yollari).
        """
        dep_map: dict[str, list[str]] = {}

        init_file = None
        source_files: list[PlannedFile] = []

        for f in files:
            if f.path.endswith("__init__.py"):
                init_file = f
            elif not f.path.startswith("tests/"):
                source_files.append(f)

        # Init tum kaynak dosyalara bagimli
        if init_file:
            dep_map[init_file.path] = [sf.path for sf in source_files]

        # Kaynak dosyalar arasi explicit bagimliliklar
        for f in files:
            if f.dependencies:
                dep_map[f.path] = list(f.dependencies)

        return dep_map

    def design_interface(self, class_name: str, methods: list[dict[str, str]]) -> dict[str, Any]:
        """Arayuz tasarimi yapar.

        Args:
            class_name: Sinif adi.
            methods: Metot tanimlari (name, return_type, description).

        Returns:
            Arayuz tanimi.
        """
        return {
            "class_name": class_name,
            "methods": methods,
            "method_count": len(methods),
        }

    def plan_test_strategy(self, plan_id: str) -> str:
        """Plan icin test stratejisi belirler.

        Args:
            plan_id: Plan ID.

        Returns:
            Test stratejisi metni.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return ""
        return plan.test_strategy

    def determine_implementation_order(self, plan_id: str) -> list[str]:
        """Uygulama sirasini getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Dosya yollari uygulama sirasinda.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        return plan.implementation_order

    def _plan_from_spec(self, spec: TechnicalSpec) -> list[PlannedFile]:
        """Spesifikasyondan dosya plani olusturur.

        Args:
            spec: Teknik spesifikasyon.

        Returns:
            Planlanmis dosyalar.
        """
        files: list[PlannedFile] = []

        # Model dosyasi
        if spec.data_models:
            files.append(PlannedFile(
                path="app/models/generated.py",
                purpose="Veri modelleri",
                estimated_lines=len(spec.data_models) * 30,
                priority=1,
            ))

        # API dosyasi
        if spec.api_endpoints:
            files.append(PlannedFile(
                path="app/api/generated_routes.py",
                purpose="API endpoint'leri",
                dependencies=["app/models/generated.py"] if spec.data_models else [],
                estimated_lines=len(spec.api_endpoints) * 20,
                priority=2,
            ))

        # Her bolum icin modul
        for i, section in enumerate(spec.sections):
            if section.section_type.value not in ("overview",):
                files.append(PlannedFile(
                    path=f"app/core/generated/{section.title[:30].lower().replace(' ', '_')}.py",
                    purpose=section.content[:80],
                    estimated_lines=80,
                    priority=i + 3,
                ))

        # Test dosyasi
        files.append(PlannedFile(
            path="tests/test_generated.py",
            purpose="Birim testler",
            dependencies=[f.path for f in files],
            estimated_lines=len(files) * 40,
            priority=100,
        ))

        return files

    def _plan_from_modules(self, modules: list[str]) -> list[PlannedFile]:
        """Modul listesinden dosya plani olusturur.

        Args:
            modules: Modul adlari.

        Returns:
            Planlanmis dosyalar.
        """
        files: list[PlannedFile] = []
        for i, module in enumerate(modules):
            files.append(PlannedFile(
                path=f"app/core/{module}.py",
                purpose=f"{module} modulu",
                estimated_lines=100,
                priority=i + 1,
            ))
        return files

    def _design_interfaces(self, files: list[PlannedFile]) -> list[dict[str, Any]]:
        """Dosyalar icin arayuz tasarimi olusturur.

        Args:
            files: Planlanmis dosyalar.

        Returns:
            Arayuz tanimlari.
        """
        interfaces: list[dict[str, Any]] = []
        for f in files:
            if f.path.endswith("__init__.py") or f.path.startswith("tests/"):
                continue
            name = f.path.split("/")[-1].replace(".py", "")
            class_name = "".join(w.capitalize() for w in name.split("_"))
            interfaces.append({
                "class_name": class_name,
                "file_path": f.path,
                "purpose": f.purpose,
            })
        return interfaces

    def _plan_test_strategy(self, files: list[PlannedFile]) -> str:
        """Test stratejisi olusturur.

        Args:
            files: Planlanmis dosyalar.

        Returns:
            Test stratejisi metni.
        """
        source_count = sum(1 for f in files if not f.path.startswith("tests/") and not f.path.endswith("__init__.py"))
        return (
            f"{source_count} modul icin birim testler yazilacak. "
            "Her sinif icin init, temel islem ve edge case testleri. "
            "Entegrasyon testleri ayri dosyada olacak."
        )

    def _determine_implementation_order(self, files: list[PlannedFile]) -> list[str]:
        """Uygulama sirasini belirler.

        Onceligi dusuk olan (yuksek priority numarasi) dosyalar
        sona birakilir. Bagimliliklar once uygulanir.

        Args:
            files: Planlanmis dosyalar.

        Returns:
            Uygulama sirasindaki dosya yollari.
        """
        # Bagimliliksiz dosyalar once
        no_deps = sorted(
            [f for f in files if not f.dependencies],
            key=lambda f: f.priority,
        )
        has_deps = sorted(
            [f for f in files if f.dependencies],
            key=lambda f: f.priority,
        )
        return [f.path for f in no_deps + has_deps]

    def get_plan(self, plan_id: str) -> CodePlan | None:
        """Kod planini getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            CodePlan nesnesi veya None.
        """
        return self._plans.get(plan_id)

    @property
    def plan_count(self) -> int:
        """Toplam plan sayisi."""
        return len(self._plans)
