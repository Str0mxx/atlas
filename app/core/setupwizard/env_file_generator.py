"""
Env Dosyasi Uretici modulu.

Sablon uretimi, degisken toplama,
dosya yazma, yedekleme, dogrulama.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EnvFileGenerator:
    """Env dosyasi uretici.

    Attributes:
        _variables: Degisken deposu.
        _stats: Istatistikler.
    """

    # Zorunlu degiskenler
    REQUIRED_VARS: list[str] = [
        "ANTHROPIC_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
    ]

    # Opsiyonel degiskenler ve varsayilan degerleri
    OPTIONAL_VARS: dict[str, str] = {
        "OPENAI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "QDRANT_URL": "http://localhost:6333",
        "LOG_LEVEL": "INFO",
        "DEBUG": "false",
        "ENVIRONMENT": "production",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    }

    ENV_TEMPLATE = """# ATLAS - Otomatik Uretilmis .env Dosyasi
# Bu dosyayi duzenleyin

# === ZORUNLU ===
ANTHROPIC_API_KEY={ANTHROPIC_API_KEY}
TELEGRAM_BOT_TOKEN={TELEGRAM_BOT_TOKEN}
DATABASE_URL={DATABASE_URL}
REDIS_URL={REDIS_URL}
SECRET_KEY={SECRET_KEY}

# === OPSIYONEL ===
OPENAI_API_KEY={OPENAI_API_KEY}
GOOGLE_API_KEY={GOOGLE_API_KEY}
QDRANT_URL={QDRANT_URL}
LOG_LEVEL={LOG_LEVEL}
DEBUG={DEBUG}
ENVIRONMENT={ENVIRONMENT}
API_HOST={API_HOST}
API_PORT={API_PORT}
CELERY_BROKER_URL={CELERY_BROKER_URL}
CELERY_RESULT_BACKEND={CELERY_RESULT_BACKEND}
"""

    def __init__(self) -> None:
        """Ureticiyi baslatir."""
        self._variables: dict[str, str] = {}
        self._stats: dict[str, int] = {
            "variables_set": 0,
            "files_generated": 0,
            "backups_created": 0,
            "validations_run": 0,
        }
        logger.info("EnvFileGenerator baslatildi")

    @property
    def variable_count(self) -> int:
        """Ayarlanan degisken sayisi."""
        return len(self._variables)

    def set_variable(
        self,
        key: str = "",
        value: str = "",
    ) -> dict[str, Any]:
        """Degisken ayarlar.

        Args:
            key: Degisken adi.
            value: Degisken degeri.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            if not key:
                return {
                    "set": False,
                    "error": "anahtar_gerekli",
                }
            self._variables[key] = value
            self._stats["variables_set"] += 1
            return {"set": True, "key": key}
        except Exception as e:
            logger.error("Degisken ayarlama hatasi: %s", e)
            return {"set": False, "error": str(e)}

    def set_variables(
        self, variables: dict | None = None
    ) -> dict[str, Any]:
        """Toplu degisken ayarlar.

        Args:
            variables: Degisken sozlugu.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            if not variables:
                return {"set": False, "error": "degisken_gerekli"}
            for k, v in variables.items():
                self._variables[k] = str(v)
                self._stats["variables_set"] += 1
            return {"set": True, "count": len(variables)}
        except Exception as e:
            logger.error("Toplu degisken ayarlama hatasi: %s", e)
            return {"set": False, "error": str(e)}

    def generate_template(self) -> dict[str, Any]:
        """Env sablonu uretir.

        Returns:
            Sablon icerigi.
        """
        try:
            # Mevcut degiskenler + varsayilanlar
            merged = dict(self.OPTIONAL_VARS)
            merged.update(self._variables)

            # Zorunlu degiskenler icin bos yer tutucu
            for var in self.REQUIRED_VARS:
                if var not in merged:
                    merged[var] = ""

            content = self.ENV_TEMPLATE.format(**merged)
            return {
                "generated": True,
                "content": content,
                "variable_count": len(merged),
            }
        except Exception as e:
            logger.error("Sablon uretme hatasi: %s", e)
            return {"generated": False, "error": str(e)}

    def backup_existing(
        self,
        env_path: str = ".env",
    ) -> dict[str, Any]:
        """Mevcut env dosyasini yedekler.

        Args:
            env_path: Env dosya yolu.

        Returns:
            Yedekleme bilgisi.
        """
        try:
            if not os.path.isfile(env_path):
                return {
                    "backed_up": False,
                    "reason": "dosya_bulunamadi",
                    "path": env_path,
                }

            import shutil
            backup_path = env_path + ".backup"
            shutil.copy2(env_path, backup_path)
            self._stats["backups_created"] += 1

            return {
                "backed_up": True,
                "original": env_path,
                "backup": backup_path,
            }
        except Exception as e:
            logger.error("Yedekleme hatasi: %s", e)
            return {"backed_up": False, "error": str(e)}

    def write_file(
        self,
        env_path: str = ".env",
        backup: bool = True,
    ) -> dict[str, Any]:
        """Env dosyasini yazar.

        Args:
            env_path: Cikti dosya yolu.
            backup: Mevcut dosyayi yedekle.

        Returns:
            Yazma bilgisi.
        """
        try:
            # Yedekle
            backup_result = None
            if backup and os.path.isfile(env_path):
                backup_result = self.backup_existing(env_path)

            # Sablon uret
            tpl = self.generate_template()
            if not tpl.get("generated"):
                return {
                    "written": False,
                    "error": tpl.get("error", "sablon_hatasi"),
                }

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(tpl["content"])

            self._stats["files_generated"] += 1
            return {
                "written": True,
                "path": env_path,
                "backup": backup_result,
                "variable_count": tpl["variable_count"],
            }
        except Exception as e:
            logger.error("Dosya yazma hatasi: %s", e)
            return {"written": False, "error": str(e)}

    def validate(
        self,
        env_path: str = ".env",
    ) -> dict[str, Any]:
        """Env dosyasini dogrular.

        Args:
            env_path: Kontrol edilecek dosya.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            self._stats["validations_run"] += 1

            if not os.path.isfile(env_path):
                return {
                    "valid": False,
                    "path": env_path,
                    "error": "dosya_bulunamadi",
                }

            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Zorunlu degiskenleri kontrol et
            missing = []
            empty = []
            for var in self.REQUIRED_VARS:
                if var not in content:
                    missing.append(var)
                else:
                    # Deger bos mu kontrol et
                    for line in content.splitlines():
                        if line.startswith(f"{var}="):
                            val = line.split("=", 1)[1].strip()
                            if not val:
                                empty.append(var)

            valid = len(missing) == 0 and len(empty) == 0
            return {
                "valid": valid,
                "path": env_path,
                "missing_vars": missing,
                "empty_vars": empty,
                "required_count": len(self.REQUIRED_VARS),
            }
        except Exception as e:
            logger.error("Dogrulama hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def load_from_file(
        self,
        env_path: str = ".env",
    ) -> dict[str, Any]:
        """Env dosyasindan degiskenleri yukler.

        Args:
            env_path: Kaynak dosya.

        Returns:
            Yukleme bilgisi.
        """
        try:
            if not os.path.isfile(env_path):
                return {
                    "loaded": False,
                    "error": "dosya_bulunamadi",
                }

            loaded = {}
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        loaded[key.strip()] = val.strip()

            self._variables.update(loaded)
            return {
                "loaded": True,
                "path": env_path,
                "variable_count": len(loaded),
            }
        except Exception as e:
            logger.error("Dosya yukleme hatasi: %s", e)
            return {"loaded": False, "error": str(e)}

    def get_variable(self, key: str = "") -> str | None:
        """Degisken getirir.

        Args:
            key: Degisken adi.

        Returns:
            Degisken degeri.
        """
        return self._variables.get(key)

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            missing_required = [
                v for v in self.REQUIRED_VARS
                if v not in self._variables or not self._variables[v]
            ]
            return {
                "retrieved": True,
                "variable_count": len(self._variables),
                "required_count": len(self.REQUIRED_VARS),
                "optional_count": len(self.OPTIONAL_VARS),
                "missing_required": missing_required,
                "ready": len(missing_required) == 0,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
