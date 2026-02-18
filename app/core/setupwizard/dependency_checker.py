"""
Bagimlilik Kontrolcusu modulu.

Python versiyonu, paket kontrolu,
sistem bagimliliklari, Docker kontrolu,
oneri uretimi.
"""

import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Bagimlilik kontrolcusu.

    Attributes:
        _checks: Kontrol sonuclari.
        _stats: Istatistikler.
    """

    REQUIRED_PACKAGES: list[str] = [
        "fastapi",
        "sqlalchemy",
        "redis",
        "celery",
        "pydantic",
        "anthropic",
        "langchain",
        "alembic",
        "pytest",
    ]

    OPTIONAL_PACKAGES: list[str] = [
        "playwright",
        "paramiko",
        "elevenlabs",
        "openai",
        "qdrant_client",
    ]

    SYSTEM_DEPS: list[str] = [
        "git",
        "python3",
        "pip",
    ]

    def __init__(self) -> None:
        """Kontrolcuyu baslatir."""
        self._checks: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "checks_run": 0,
            "checks_passed": 0,
            "checks_failed": 0,
            "checks_skipped": 0,
        }
        logger.info("DependencyChecker baslatildi")

    @property
    def check_count(self) -> int:
        """Yapilan kontrol sayisi."""
        return len(self._checks)

    def check_python_version(
        self,
        min_version: tuple = (3, 11),
    ) -> dict[str, Any]:
        """Python versiyonunu kontrol eder.

        Args:
            min_version: Minimum versiyon (major, minor).

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1
            vi = sys.version_info
            current = (vi.major, vi.minor)
            passed = current >= min_version

            result = {
                "passed": passed,
                "check": "python_version",
                "current": f"{vi.major}.{vi.minor}.{vi.micro}",
                "required": f"{min_version[0]}.{min_version[1]}+",
            }
            self._checks["python_version"] = result
            if passed:
                self._stats["checks_passed"] += 1
            else:
                self._stats["checks_failed"] += 1
            return result
        except Exception as e:
            logger.error("Python versiyon kontrolu hatasi: %s", e)
            self._stats["checks_failed"] += 1
            return {"passed": False, "check": "python_version", "error": str(e)}

    def check_package(
        self,
        package_name: str = "",
        required: bool = True,
    ) -> dict[str, Any]:
        """Python paketini kontrol eder.

        Args:
            package_name: Paket adi.
            required: Zorunlu mu.

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1

            if not package_name:
                return {
                    "passed": False,
                    "check": "package",
                    "error": "paket_adi_gerekli",
                }

            try:
                import importlib
                spec = importlib.util.find_spec(
                    package_name.replace("-", "_")
                )
                installed = spec is not None
            except (ModuleNotFoundError, ValueError):
                installed = False

            # Zorunlu degilse, kurulu olmasa da passed
            passed = installed or not required

            result = {
                "passed": passed,
                "check": "package",
                "package": package_name,
                "installed": installed,
                "required": required,
            }
            key = f"package_{package_name}"
            self._checks[key] = result
            if passed:
                self._stats["checks_passed"] += 1
            else:
                self._stats["checks_failed"] += 1
            return result
        except Exception as e:
            logger.error("Paket kontrolu hatasi: %s", e)
            self._stats["checks_failed"] += 1
            return {"passed": False, "check": "package", "error": str(e)}

    def check_required_packages(self) -> dict[str, Any]:
        """Zorunlu paketleri kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        try:
            results = []
            missing = []

            for pkg in self.REQUIRED_PACKAGES:
                r = self.check_package(pkg, required=True)
                results.append(r)
                if not r.get("installed"):
                    missing.append(pkg)

            passed = len(missing) == 0
            return {
                "passed": passed,
                "check": "required_packages",
                "total": len(self.REQUIRED_PACKAGES),
                "missing": missing,
                "missing_count": len(missing),
            }
        except Exception as e:
            logger.error("Zorunlu paket kontrolu hatasi: %s", e)
            return {"passed": False, "error": str(e)}

    def check_optional_packages(self) -> dict[str, Any]:
        """Opsiyonel paketleri kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        try:
            results = []
            installed_list = []

            for pkg in self.OPTIONAL_PACKAGES:
                r = self.check_package(pkg, required=False)
                results.append(r)
                if r.get("installed"):
                    installed_list.append(pkg)

            return {
                "passed": True,  # Opsiyonel, her zaman passed
                "check": "optional_packages",
                "total": len(self.OPTIONAL_PACKAGES),
                "installed": installed_list,
                "installed_count": len(installed_list),
            }
        except Exception as e:
            logger.error("Opsiyonel paket kontrolu hatasi: %s", e)
            return {"passed": False, "error": str(e)}

    def check_system_dependency(
        self,
        dep_name: str = "",
    ) -> dict[str, Any]:
        """Sistem bagimliligini kontrol eder.

        Args:
            dep_name: Bagimlilik adi.

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1

            if not dep_name:
                return {
                    "passed": False,
                    "check": "system_dep",
                    "error": "bagimlilik_adi_gerekli",
                }

            import shutil
            found = shutil.which(dep_name) is not None

            result = {
                "passed": found,
                "check": "system_dep",
                "dependency": dep_name,
                "found": found,
            }
            key = f"sysdep_{dep_name}"
            self._checks[key] = result
            if found:
                self._stats["checks_passed"] += 1
            else:
                self._stats["checks_failed"] += 1
            return result
        except Exception as e:
            logger.error("Sistem bagimlilik kontrolu hatasi: %s", e)
            self._stats["checks_failed"] += 1
            return {"passed": False, "check": "system_dep", "error": str(e)}

    def check_docker(self) -> dict[str, Any]:
        """Docker kurulumunu kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1
            import shutil

            docker_found = shutil.which("docker") is not None
            compose_found = shutil.which("docker-compose") is not None

            passed = docker_found

            result = {
                "passed": passed,
                "check": "docker",
                "docker_found": docker_found,
                "compose_found": compose_found,
            }
            self._checks["docker"] = result
            if passed:
                self._stats["checks_passed"] += 1
            else:
                self._stats["checks_failed"] += 1
            return result
        except Exception as e:
            logger.error("Docker kontrolu hatasi: %s", e)
            self._stats["checks_failed"] += 1
            return {"passed": False, "check": "docker", "error": str(e)}

    def check_env_file(
        self,
        env_path: str = ".env",
    ) -> dict[str, Any]:
        """Env dosyasini kontrol eder.

        Args:
            env_path: Env dosya yolu.

        Returns:
            Kontrol sonucu.
        """
        try:
            self._stats["checks_run"] += 1
            import os

            exists = os.path.isfile(env_path)
            result = {
                "passed": exists,
                "check": "env_file",
                "path": env_path,
                "exists": exists,
            }
            self._checks["env_file"] = result
            if exists:
                self._stats["checks_passed"] += 1
            else:
                self._stats["checks_failed"] += 1
            return result
        except Exception as e:
            logger.error("Env dosya kontrolu hatasi: %s", e)
            self._stats["checks_failed"] += 1
            return {"passed": False, "check": "env_file", "error": str(e)}

    def get_recommendations(self) -> list[str]:
        """Oneri listesi uretir.

        Returns:
            Oneri listesi.
        """
        recommendations = []

        for key, result in self._checks.items():
            if not result.get("passed"):
                check = result.get("check", "")
                if check == "python_version":
                    recommendations.append(
                        "Python 3.11+ surumune yukseltin"
                    )
                elif check == "package":
                    pkg = result.get("package", "")
                    if result.get("required"):
                        recommendations.append(
                            f"pip install {pkg}"
                        )
                elif check == "docker":
                    recommendations.append(
                        "Docker Desktop kurun: docker.com"
                    )
                elif check == "env_file":
                    recommendations.append(
                        ".env dosyasi olusturun (.env.example kopyalayin)"
                    )

        return recommendations

    def run_all(self) -> dict[str, Any]:
        """Tum kontrolleri calistirir.

        Returns:
            Toplu kontrol sonucu.
        """
        try:
            results = []
            results.append(self.check_python_version())
            results.append(self.check_required_packages())
            results.append(self.check_optional_packages())
            results.append(self.check_docker())
            results.append(self.check_env_file())

            for dep in self.SYSTEM_DEPS:
                results.append(self.check_system_dependency(dep))

            passed = sum(1 for r in results if r.get("passed"))
            failed = sum(1 for r in results if not r.get("passed"))

            recommendations = self.get_recommendations()

            return {
                "completed": True,
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "ready": failed == 0,
                "recommendations": recommendations,
                "results": results,
            }
        except Exception as e:
            logger.error("Toplu kontrol hatasi: %s", e)
            return {"completed": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            recommendations = self.get_recommendations()
            return {
                "retrieved": True,
                "check_count": len(self._checks),
                "checks_passed": self._stats["checks_passed"],
                "checks_failed": self._stats["checks_failed"],
                "recommendation_count": len(recommendations),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
