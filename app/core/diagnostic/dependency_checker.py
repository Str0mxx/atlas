"""ATLAS Bagimlilik Kontrolcu modulu.

Eksik bagimliliklar, surum catismalari,
dongusel bagimliliklar, kaldirilmis paketler
ve guvenlik acikliklari.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Bagimlilik kontrolcu.

    Sistem bagimliklarini kontrol eder
    ve sorunlari tespit eder.

    Attributes:
        _packages: Kayitli paketler.
        _dependencies: Bagimlilik grafi.
        _issues: Tespit edilen sorunlar.
        _deprecated: Kaldirilmis paketler.
        _vulnerabilities: Guvenlik acikliklari.
    """

    def __init__(self) -> None:
        """Bagimlilik kontrolcuyu baslatir."""
        self._packages: dict[str, dict[str, Any]] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._issues: list[dict[str, Any]] = []
        self._deprecated: set[str] = set()
        self._vulnerabilities: list[dict[str, Any]] = []

        logger.info("DependencyChecker baslatildi")

    def register_package(
        self,
        name: str,
        version: str,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Paket kaydeder.

        Args:
            name: Paket adi.
            version: Surum.
            dependencies: Bagimliliklar.

        Returns:
            Kayit bilgisi.
        """
        self._packages[name] = {
            "version": version,
            "dependencies": dependencies or [],
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dependencies[name] = dependencies or []

        return self._packages[name]

    def check_missing(self) -> list[dict[str, Any]]:
        """Eksik bagimliklar kontrol eder.

        Returns:
            Eksik bagimlilik listesi.
        """
        missing: list[dict[str, Any]] = []

        for pkg, deps in self._dependencies.items():
            for dep in deps:
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                if dep_name not in self._packages:
                    issue = {
                        "type": "missing",
                        "package": dep_name,
                        "required_by": pkg,
                        "requirement": dep,
                    }
                    missing.append(issue)
                    self._issues.append(issue)

        return missing

    def check_version_conflicts(self) -> list[dict[str, Any]]:
        """Surum catismalarini kontrol eder.

        Returns:
            Catisma listesi.
        """
        conflicts: list[dict[str, Any]] = []
        requirements: dict[str, list[tuple[str, str]]] = {}

        for pkg, deps in self._dependencies.items():
            for dep in deps:
                if "==" in dep:
                    parts = dep.split("==")
                    dep_name = parts[0].strip()
                    req_version = parts[1].strip()
                    requirements.setdefault(dep_name, []).append(
                        (pkg, req_version),
                    )

        for dep_name, reqs in requirements.items():
            versions = set(v for _, v in reqs)
            if len(versions) > 1:
                conflict = {
                    "type": "version_conflict",
                    "package": dep_name,
                    "conflicting_versions": list(versions),
                    "required_by": [r[0] for r in reqs],
                }
                conflicts.append(conflict)
                self._issues.append(conflict)

        return conflicts

    def check_circular(self) -> list[list[str]]:
        """Dongusel bagimliliklari kontrol eder.

        Returns:
            Dongu listesi.
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        path: list[str] = []

        def _dfs(node: str, stack: set[str]) -> None:
            if node in stack:
                # Dongu bulundu
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            stack.add(node)
            path.append(node)

            for dep in self._dependencies.get(node, []):
                dep_name = dep.split(">=")[0].split("==")[0].strip()
                _dfs(dep_name, stack)

            path.pop()
            stack.discard(node)

        for pkg in self._packages:
            visited.clear()
            path.clear()
            _dfs(pkg, set())

        for cycle in cycles:
            self._issues.append({
                "type": "circular",
                "cycle": cycle,
            })

        return cycles

    def mark_deprecated(
        self,
        package: str,
        replacement: str = "",
    ) -> None:
        """Paketi kaldirilmis olarak isaretle.

        Args:
            package: Paket adi.
            replacement: Yerine gelen paket.
        """
        self._deprecated.add(package)
        self._issues.append({
            "type": "deprecated",
            "package": package,
            "replacement": replacement,
        })

    def check_deprecated(self) -> list[dict[str, Any]]:
        """Kaldirilmis paketleri kontrol eder.

        Returns:
            Kaldirilmis paket listesi.
        """
        found = []
        for pkg in self._packages:
            if pkg in self._deprecated:
                found.append({
                    "type": "deprecated",
                    "package": pkg,
                    "version": self._packages[pkg]["version"],
                })
        return found

    def add_vulnerability(
        self,
        package: str,
        cve_id: str,
        severity: str = "medium",
        description: str = "",
    ) -> dict[str, Any]:
        """Guvenlik acikligi ekler.

        Args:
            package: Paket adi.
            cve_id: CVE ID.
            severity: Ciddiyet.
            description: Aciklama.

        Returns:
            Aciklik kaydi.
        """
        vuln = {
            "package": package,
            "cve_id": cve_id,
            "severity": severity,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._vulnerabilities.append(vuln)
        self._issues.append({"type": "vulnerability", **vuln})

        return vuln

    def check_vulnerabilities(self) -> list[dict[str, Any]]:
        """Guvenlik acikliklarini kontrol eder.

        Returns:
            Aciklik listesi.
        """
        found = []
        for vuln in self._vulnerabilities:
            if vuln["package"] in self._packages:
                found.append(vuln)
        return found

    def full_check(self) -> dict[str, Any]:
        """Tam bagimlilik kontrolu yapar.

        Returns:
            Kontrol sonucu.
        """
        missing = self.check_missing()
        conflicts = self.check_version_conflicts()
        circular = self.check_circular()
        deprecated = self.check_deprecated()
        vulns = self.check_vulnerabilities()

        total_issues = (
            len(missing) + len(conflicts) + len(circular)
            + len(deprecated) + len(vulns)
        )

        return {
            "healthy": total_issues == 0,
            "missing": missing,
            "conflicts": conflicts,
            "circular": circular,
            "deprecated": deprecated,
            "vulnerabilities": vulns,
            "total_issues": total_issues,
            "packages_checked": len(self._packages),
        }

    def get_dependency_tree(
        self,
        package: str,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Bagimlilik agacini getirir.

        Args:
            package: Paket adi.
            depth: Maks derinlik.

        Returns:
            Agac yapisi.
        """
        if depth <= 0 or package not in self._packages:
            return {"name": package, "children": []}

        children = []
        for dep in self._dependencies.get(package, []):
            dep_name = dep.split(">=")[0].split("==")[0].strip()
            children.append(
                self.get_dependency_tree(dep_name, depth - 1),
            )

        return {
            "name": package,
            "version": self._packages.get(package, {}).get("version", "?"),
            "children": children,
        }

    @property
    def package_count(self) -> int:
        """Paket sayisi."""
        return len(self._packages)

    @property
    def issue_count(self) -> int:
        """Sorun sayisi."""
        return len(self._issues)

    @property
    def vulnerability_count(self) -> int:
        """Aciklik sayisi."""
        return len(self._vulnerabilities)
