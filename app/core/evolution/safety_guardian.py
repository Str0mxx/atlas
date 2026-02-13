"""ATLAS Guvenlik Koruyucu modulu.

Degisiklik siddeti siniflandirma, otomatik onay,
zararli kod tespiti ve kaynak limit zorlama.
"""

import logging
import re

from app.models.evolution import (
    ChangeSeverity,
    CodeChange,
    SafetyCheckResult,
)

logger = logging.getLogger(__name__)

# Zararli kod kaliplari
_HARMFUL_PATTERNS: list[tuple[str, str]] = [
    (r"os\.system\(", "os.system kullanimi"),
    (r"subprocess\.call.*shell\s*=\s*True", "shell injection riski"),
    (r"eval\(", "eval kullanimi"),
    (r"exec\(", "exec kullanimi"),
    (r"__import__\(", "dinamik import"),
    (r"rm\s+-rf", "tehlikeli silme komutu"),
    (r"DROP\s+TABLE", "veritabani silme"),
    (r"DELETE\s+FROM.*WHERE\s+1", "toplu veri silme"),
    (r"chmod\s+777", "guvenli olmayan yetkilendirme"),
    (r"password\s*=\s*['\"]", "hardcoded sifre"),
]

# Kaynak limitleri
_DEFAULT_RESOURCE_LIMITS = {
    "max_cpu_pct": 80.0,
    "max_memory_mb": 512.0,
    "max_file_changes": 20,
    "max_diff_lines": 500,
}


class SafetyGuardian:
    """Guvenlik koruyucu sistemi.

    Degisiklikleri siniflandirir, zararli kod tespit eder,
    minor degisiklikleri otomatik onaylar, major/critical icin
    insan onayi gerektirir.

    Attributes:
        _results: Guvenlik kontrol sonuclari.
        _auto_approve_minor: Minor otomatik onay.
        _resource_limits: Kaynak limitleri.
    """

    def __init__(
        self,
        auto_approve_minor: bool = True,
        resource_limits: dict[str, float] | None = None,
    ) -> None:
        """Guvenlik koruyucuyu baslatir.

        Args:
            auto_approve_minor: Minor degisiklikler otomatik onaylansin mi.
            resource_limits: Kaynak limitleri.
        """
        self._results: list[SafetyCheckResult] = []
        self._auto_approve_minor = auto_approve_minor
        self._resource_limits = resource_limits or dict(_DEFAULT_RESOURCE_LIMITS)

        logger.info(
            "SafetyGuardian baslatildi (auto_minor=%s)", auto_approve_minor
        )

    def classify_severity(self, change: CodeChange) -> ChangeSeverity:
        """Degisiklik siddetini siniflandirir.

        Args:
            change: Kod degisikligi.

        Returns:
            ChangeSeverity degeri.
        """
        diff = change.diff
        lines = diff.split("\n")
        additions = sum(1 for l in lines if l.startswith("+"))
        deletions = sum(1 for l in lines if l.startswith("-"))
        total_changes = additions + deletions

        # Buyuk degisiklikler
        if total_changes > 50:
            return ChangeSeverity.CRITICAL
        if total_changes > 20:
            return ChangeSeverity.MAJOR

        # Degisiklik tipi
        if change.change_type in ("add", "refactor"):
            return ChangeSeverity.MAJOR
        if change.change_type in ("config", "docs"):
            return ChangeSeverity.MINOR

        return change.severity

    def check_safety(self, change: CodeChange) -> SafetyCheckResult:
        """Guvenlik kontrolu yapar.

        Args:
            change: Kontrol edilecek degisiklik.

        Returns:
            SafetyCheckResult nesnesi.
        """
        issues: list[str] = []

        # Zararli kod kontrolu
        harmful = self._detect_harmful_code(change.diff)
        issues.extend(harmful)

        # Kaynak limit kontrolu
        resource_impact = self._check_resource_impact(change)

        # Ciddiyet siniflandirmasi
        severity = self.classify_severity(change)

        # Onay gereksinimi
        requires_approval = self._needs_approval(severity, issues)

        is_safe = len(issues) == 0

        result = SafetyCheckResult(
            change_id=change.id,
            severity=severity,
            is_safe=is_safe,
            requires_approval=requires_approval,
            issues=issues,
            resource_impact=resource_impact,
        )

        self._results.append(result)
        logger.info(
            "Guvenlik kontrolu: %s (safe=%s, approval=%s)",
            change.file_path, is_safe, requires_approval,
        )
        return result

    def check_batch(self, changes: list[CodeChange]) -> list[SafetyCheckResult]:
        """Toplu guvenlik kontrolu yapar.

        Args:
            changes: Degisiklik listesi.

        Returns:
            SafetyCheckResult listesi.
        """
        return [self.check_safety(c) for c in changes]

    def can_auto_approve(self, result: SafetyCheckResult) -> bool:
        """Otomatik onaylanabilir mi kontrol eder.

        Args:
            result: Guvenlik kontrol sonucu.

        Returns:
            Otomatik onaylanabilir mi.
        """
        if not self._auto_approve_minor:
            return False
        if not result.is_safe:
            return False
        if result.severity != ChangeSeverity.MINOR:
            return False
        return not result.requires_approval

    def enforce_resource_limits(self, usage: dict[str, float]) -> list[str]:
        """Kaynak limitlerini zorlar.

        Args:
            usage: Mevcut kaynak kullanimi.

        Returns:
            Ihlal listesi.
        """
        violations: list[str] = []

        for key, limit in self._resource_limits.items():
            actual = usage.get(key, 0.0)
            if actual > limit:
                violations.append(f"{key}: {actual:.1f} > {limit:.1f}")

        return violations

    def _detect_harmful_code(self, diff: str) -> list[str]:
        """Zararli kod kaliplarini tespit eder."""
        issues: list[str] = []

        for pattern, description in _HARMFUL_PATTERNS:
            if re.search(pattern, diff, re.IGNORECASE):
                issues.append(description)

        return issues

    def _check_resource_impact(self, change: CodeChange) -> dict[str, float]:
        """Kaynak etkisini hesaplar."""
        lines = change.diff.split("\n")
        total_lines = len(lines)

        return {
            "diff_lines": float(total_lines),
            "estimated_cpu_impact": min(total_lines * 0.1, 100.0),
            "estimated_memory_impact": min(total_lines * 0.05, 100.0),
        }

    def _needs_approval(self, severity: ChangeSeverity, issues: list[str]) -> bool:
        """Onay gereksinimi belirler."""
        if issues:
            return True
        if severity == ChangeSeverity.CRITICAL:
            return True
        if severity == ChangeSeverity.MAJOR:
            return True
        return False

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)

    @property
    def safe_count(self) -> int:
        """Guvenli sonuc sayisi."""
        return sum(1 for r in self._results if r.is_safe)

    @property
    def unsafe_count(self) -> int:
        """Guvenli olmayan sonuc sayisi."""
        return sum(1 for r in self._results if not r.is_safe)
