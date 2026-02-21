"""OpenClaw toplu ithalat orkestratoru.

Dizinleri tarar, guvenlik kontrolu yapar,
donusturur ve kayit defterine kaydeder.
"""

import json
import logging
import os
import time
from typing import Any

from app.core.openclaw.skill_importer import (
    OpenClawSkillImporter,
)
from app.core.openclaw.security_scanner import (
    OpenClawSecurityScanner,
)
from app.core.openclaw.skill_converter import (
    OpenClawSkillConverter,
)
from app.core.skills.base_skill import (
    BaseSkill,
)
from app.core.skills.skill_registry import (
    SkillRegistry,
)
from app.models.openclaw_models import (
    ImportStatistics,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)

_MAX_HISTORY = 5000


class OpenClawBatchImporter:
    """OpenClaw toplu ithalat orkestratoru.

    Tum pipeline'i yonetir:
    Scan -> Parse -> Security -> Convert -> Register

    Attributes:
        _importer: SKILL.md ayristirici.
        _scanner: Guvenlik tarayici.
        _converter: Beceri donusturucu.
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        min_score: int = 70,
    ) -> None:
        """OpenClawBatchImporter baslatir.

        Args:
            registry: Beceri kayit defteri.
            min_score: Minimum guvenlik puani.
        """
        self._importer = OpenClawSkillImporter()
        self._scanner = OpenClawSecurityScanner()
        self._converter = OpenClawSkillConverter()
        self._registry = (
            registry or SkillRegistry()
        )
        self._min_score = min_score
        self._imported_skills: list[
            BaseSkill
        ] = []
        self._scan_results: list[
            SecurityScanResult
        ] = []
        self._stats = ImportStatistics()
        self._history: list[
            dict[str, Any]
        ] = []

    @property
    def importer(self) -> OpenClawSkillImporter:
        """Importer'a erisim."""
        return self._importer

    @property
    def scanner(self) -> OpenClawSecurityScanner:
        """Scanner'a erisim."""
        return self._scanner

    @property
    def converter(self) -> OpenClawSkillConverter:
        """Converter'a erisim."""
        return self._converter

    @property
    def registry(self) -> SkillRegistry:
        """Registry'ye erisim."""
        return self._registry

    @property
    def stats(self) -> ImportStatistics:
        """Istatistiklere erisim."""
        return self._stats

    # ---- Ana Ithalat ----

    def import_all(
        self,
        repo_dirs: list[
            tuple[str, str]
        ],
    ) -> ImportStatistics:
        """Tum repolari ithal eder.

        Args:
            repo_dirs: (yol, repo_adi) ciftleri.

        Returns:
            Ithalat istatistikleri.
        """
        self._stats = ImportStatistics()
        self._imported_skills.clear()
        self._scan_results.clear()

        for path, repo_name in repo_dirs:
            self._import_repo(path, repo_name)

        # Ortalama guvenlik puani
        if self._scan_results:
            total_score = sum(
                r.score
                for r in self._scan_results
            )
            self._stats.avg_security_score = (
                round(
                    total_score
                    / len(self._scan_results),
                    2,
                )
            )

        self._record_history(
            "import_all",
            "batch",
            f"imported={self._stats.imported} "
            f"total={self._stats.total_found}",
        )

        return self._stats

    def _import_repo(
        self,
        root_path: str,
        repo_name: str,
    ) -> None:
        """Tek bir repoyu ithal eder.

        Args:
            root_path: Repo dizin yolu.
            repo_name: Repo adi.
        """
        if not os.path.isdir(root_path):
            self._stats.errors.append(
                f"Dizin bulunamadi: {root_path}",
            )
            return

        # 1. Tara ve ayristir
        raws = self._importer.scan_directory(
            root_path,
            source_repo=repo_name,
        )

        self._stats.total_found += len(raws)
        self._stats.parsed_ok += len(raws)

        repo_count = 0

        for raw in raws:
            # 2. Guvenlik taramas
            scan = self._scanner.scan_skill(
                raw,
                min_score=self._min_score,
            )
            self._scan_results.append(scan)

            # Risk seviyesi istatistigi
            rl = scan.risk_level
            self._stats.by_risk_level[rl] = (
                self._stats.by_risk_level.get(
                    rl, 0,
                ) + 1
            )

            if not scan.passed:
                self._stats.skipped += 1
                continue

            self._stats.passed_security += 1

            # 3. Duplikat kontrolu
            name = (
                raw.frontmatter.name
                or raw.file_path
            )
            if self._check_duplicate(name):
                self._stats.duplicates += 1
                continue

            # 4. Donusum
            instance = (
                self._converter
                .create_skill_instance(
                    raw, scan,
                )
            )
            if not instance:
                self._stats.failed += 1
                self._stats.errors.append(
                    f"Donusum hatasi: "
                    f"{raw.file_path}",
                )
                continue

            # 5. Kayit
            if self._registry.register(instance):
                self._imported_skills.append(
                    instance,
                )
                self._stats.imported += 1
                repo_count += 1

                # Kategori istatistigi
                cat = instance.CATEGORY
                self._stats.by_category[cat] = (
                    self._stats.by_category.get(
                        cat, 0,
                    ) + 1
                )
            else:
                self._stats.failed += 1

        # Repo istatistigi
        self._stats.by_repo[repo_name] = (
            repo_count
        )

    def _check_duplicate(
        self,
        name: str,
    ) -> bool:
        """Duplikat kontrolu yapar.

        Yerel ATLAS becerileri her zaman oncelikli.

        Args:
            name: Beceri adi.

        Returns:
            Duplikat ise True.
        """
        existing = self._registry.get_by_name(
            name,
        )
        if existing is None:
            return False

        # Yerel ATLAS becerisi ise atla
        if not existing.SKILL_ID.startswith(
            "OC_",
        ):
            return True

        # Onceki OC becerisi varsa atla
        return True

    # ---- Kayit ----

    def register_imported_skills(
        self,
        registry: SkillRegistry | None = None,
    ) -> int:
        """Ithal edilen becerileri kaydeder.

        Args:
            registry: Hedef kayit defteri.

        Returns:
            Kaydedilen sayi.
        """
        target = registry or self._registry
        count = 0
        for skill in self._imported_skills:
            if target.get(skill.SKILL_ID):
                continue
            if target.register(skill):
                count += 1
        return count

    # ---- Raporlama ----

    def export_reports(
        self,
        output_dir: str = "reports",
    ) -> str:
        """Ithalat raporlarini JSON olarak verir.

        Args:
            output_dir: Cikti dizini.

        Returns:
            Rapor dosya yolu.
        """
        os.makedirs(output_dir, exist_ok=True)

        report = {
            "statistics": (
                self._stats.model_dump()
            ),
            "scan_results": [
                r.model_dump()
                for r in self._scan_results
            ],
            "imported_skills": [
                {
                    "skill_id": s.SKILL_ID,
                    "name": s.NAME,
                    "category": s.CATEGORY,
                    "risk_level": s.RISK_LEVEL,
                }
                for s in self._imported_skills
            ],
        }

        path = os.path.join(
            output_dir,
            "openclaw_import_report.json",
        )

        with open(
            path, "w", encoding="utf-8",
        ) as f:
            json.dump(
                report, f,
                indent=2,
                ensure_ascii=False,
            )

        self._record_history(
            "export",
            path,
            f"skills={len(self._imported_skills)}",
        )
        return path

    def get_imported_skills(
        self,
    ) -> list[BaseSkill]:
        """Ithal edilen becerileri dondurur.

        Returns:
            Beceri listesi.
        """
        return list(self._imported_skills)

    def get_scan_results(
        self,
    ) -> list[SecurityScanResult]:
        """Tarama sonuclarini dondurur.

        Returns:
            Sonuc listesi.
        """
        return list(self._scan_results)

    # ---- Dahili ----

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-2500:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "imported": self._stats.imported,
            "total_found": (
                self._stats.total_found
            ),
            "passed_security": (
                self._stats.passed_security
            ),
            "duplicates": (
                self._stats.duplicates
            ),
            "skipped": self._stats.skipped,
            "failed": self._stats.failed,
        }
