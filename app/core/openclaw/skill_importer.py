"""OpenClaw SKILL.md dosya ayristirici.

Dizin agaclarini tarar, SKILL.md dosyalarini bulur,
YAML frontmatter ve markdown govdesini ayristirir.
"""

import logging
import os
import re
import time
from typing import Any

from app.models.openclaw_models import (
    OpenClawFrontmatter,
    OpenClawSkillRaw,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 5000
_MAX_HISTORY = 5000
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL,
)


class OpenClawSkillImporter:
    """SKILL.md dosyalarindan beceri icerigini ayristirir.

    Dizin agaclarini tarar, frontmatter ve
    govde icerigini cikarir.

    Attributes:
        _records: Ayristirma kayitlari.
    """

    def __init__(self) -> None:
        """OpenClawSkillImporter baslatir."""
        self._records: dict[
            str, OpenClawSkillRaw
        ] = {}
        self._record_order: list[str] = []
        self._total_ops: int = 0
        self._total_success: int = 0
        self._total_failed: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

    # ---- Dizin Tarama ----

    def scan_directory(
        self,
        root_path: str,
        source_repo: str = "",
    ) -> list[OpenClawSkillRaw]:
        """Dizin agacini SKILL.md dosyalari icin tarar.

        Args:
            root_path: Kok dizin yolu.
            source_repo: Kaynak repo adi.

        Returns:
            Ayristirilan beceri listesi.
        """
        results: list[OpenClawSkillRaw] = []

        if not os.path.isdir(root_path):
            logger.warning(
                "Dizin bulunamadi: %s",
                root_path,
            )
            return results

        for dirpath, _dirs, files in os.walk(
            root_path,
        ):
            for fname in files:
                if fname.upper() == "SKILL.MD":
                    fpath = os.path.join(
                        dirpath, fname,
                    )
                    raw = self.parse_skill_md(
                        fpath,
                        source_repo=source_repo,
                    )
                    if raw:
                        results.append(raw)

        self._record_history(
            "scan_directory",
            root_path,
            f"found={len(results)}",
        )
        return results

    # ---- Dosya Ayristirma ----

    def parse_skill_md(
        self,
        file_path: str,
        source_repo: str = "",
    ) -> OpenClawSkillRaw | None:
        """Tek bir SKILL.md dosyasini ayristirir.

        Args:
            file_path: Dosya yolu.
            source_repo: Kaynak repo adi.

        Returns:
            Ham beceri verisi veya None.
        """
        self._total_ops += 1

        try:
            with open(
                file_path, "r",
                encoding="utf-8",
                errors="replace",
            ) as f:
                content = f.read()
        except Exception as e:
            self._total_failed += 1
            logger.warning(
                "Dosya okunamadi: %s: %s",
                file_path, e,
            )
            return None

        errors: list[str] = []
        frontmatter, body = (
            self._extract_frontmatter(
                content, errors,
            )
        )

        raw = OpenClawSkillRaw(
            file_path=file_path,
            frontmatter=frontmatter,
            body=body,
            source_repo=source_repo,
            parse_errors=errors,
        )

        key = file_path
        self._records[key] = raw
        self._record_order.append(key)
        if len(self._records) > _MAX_RECORDS:
            self._rotate()

        self._total_success += 1
        return raw

    # ---- Frontmatter ----

    def _extract_frontmatter(
        self,
        content: str,
        errors: list[str],
    ) -> tuple[OpenClawFrontmatter, str]:
        """YAML frontmatter ve govdeyi cikarir.

        Args:
            content: Dosya icerigi.
            errors: Hata listesi (degistirilir).

        Returns:
            (frontmatter, body) cifti.
        """
        match = _FRONTMATTER_RE.match(content)
        if not match:
            return OpenClawFrontmatter(), content

        yaml_text = match.group(1)
        body = content[match.end():]

        parsed = self._parse_yaml(
            yaml_text, errors,
        )

        fm = self._dict_to_frontmatter(
            parsed, errors,
        )
        return fm, body

    def _parse_yaml(
        self,
        yaml_text: str,
        errors: list[str],
    ) -> dict[str, Any]:
        """YAML metnini sozluge ayristirir.

        Args:
            yaml_text: YAML metni.
            errors: Hata listesi.

        Returns:
            Ayristirilan sozluk.
        """
        try:
            import yaml
            result = yaml.safe_load(yaml_text)
            if isinstance(result, dict):
                return result
            errors.append(
                "YAML icerik sozluk degil",
            )
            return {}
        except ImportError:
            return self._parse_nested_yaml(
                yaml_text, errors,
            )
        except Exception as e:
            errors.append(f"YAML hatasi: {e}")
            return self._parse_nested_yaml(
                yaml_text, errors,
            )

    def _parse_nested_yaml(
        self,
        text: str,
        errors: list[str],
    ) -> dict[str, Any]:
        """Manuel ic ice YAML ayristirici.

        Args:
            text: YAML metni.
            errors: Hata listesi.

        Returns:
            Ayristirilan sozluk.
        """
        result: dict[str, Any] = {}
        lines = text.split("\n")
        current_key = ""
        current_list: list[str] | None = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(
                line.lstrip(),
            )

            # Liste elemani
            if stripped.startswith("- "):
                val = stripped[2:].strip()
                if current_list is not None:
                    current_list.append(val)
                elif current_key:
                    result[current_key] = [val]
                    current_list = result[
                        current_key
                    ]
                continue

            # Anahtar: deger cifti
            if ":" in stripped:
                current_list = None
                parts = stripped.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip() if len(
                    parts,
                ) > 1 else ""

                if indent == 0:
                    current_key = key
                    if val:
                        result[key] = val
                    else:
                        result[key] = {}
                elif current_key:
                    parent = result.get(
                        current_key,
                    )
                    if isinstance(parent, dict):
                        if val:
                            parent[key] = val
                        else:
                            parent[key] = {}

        return result

    def _dict_to_frontmatter(
        self,
        data: dict[str, Any],
        errors: list[str],
    ) -> OpenClawFrontmatter:
        """Sozlugu OpenClawFrontmatter'a donusturur.

        Args:
            data: Ayristirilan sozluk.
            errors: Hata listesi.

        Returns:
            Frontmatter nesnesi.
        """
        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            metadata = {}

        openclaw = metadata.get("openclaw", {})
        if isinstance(openclaw, str):
            openclaw = {}

        requires = openclaw.get("requires", {})
        if isinstance(requires, str):
            requires = {}

        tags_raw = data.get("tags", [])
        if isinstance(tags_raw, str):
            tags_raw = [
                t.strip()
                for t in tags_raw.split(",")
                if t.strip()
            ]
        elif not isinstance(tags_raw, list):
            tags_raw = []

        os_raw = openclaw.get("os", [])
        if isinstance(os_raw, str):
            os_raw = [os_raw]
        elif not isinstance(os_raw, list):
            os_raw = []

        env_raw = requires.get("env", [])
        if isinstance(env_raw, str):
            env_raw = [env_raw]
        elif not isinstance(env_raw, list):
            env_raw = []

        bins_raw = requires.get("bins", [])
        if isinstance(bins_raw, str):
            bins_raw = [bins_raw]
        elif not isinstance(bins_raw, list):
            bins_raw = []

        install_raw = requires.get(
            "install", [],
        )
        if isinstance(install_raw, str):
            install_raw = [install_raw]
        elif not isinstance(install_raw, list):
            install_raw = []

        extra: dict[str, Any] = {}
        known_keys = {
            "name", "description", "version",
            "author", "tags", "category",
            "metadata",
        }
        for k, v in data.items():
            if k not in known_keys:
                extra[k] = v

        return OpenClawFrontmatter(
            name=str(data.get("name", "")),
            description=str(
                data.get("description", ""),
            ),
            version=str(
                data.get("version", "1.0.0"),
            ),
            author=str(
                data.get("author", ""),
            ),
            tags=tags_raw,
            category=str(
                data.get("category", ""),
            ),
            primary_env=str(
                openclaw.get("primaryEnv", ""),
            ),
            os=os_raw,
            requires_env=env_raw,
            requires_bins=bins_raw,
            requires_install=install_raw,
            extra=extra,
        )

    # ---- Sorgulama ----

    def get_parsed(
        self,
        file_path: str,
    ) -> OpenClawSkillRaw | None:
        """Ayristirilan beceriyi dondurur.

        Args:
            file_path: Dosya yolu.

        Returns:
            Ham beceri verisi veya None.
        """
        return self._records.get(file_path)

    def list_parsed(
        self,
        limit: int = 100,
    ) -> list[OpenClawSkillRaw]:
        """Ayristirilan becerileri listeler.

        Args:
            limit: Maks sayi.

        Returns:
            Beceri listesi.
        """
        keys = list(
            reversed(self._record_order),
        )[:limit]
        result: list[OpenClawSkillRaw] = []
        for k in keys:
            r = self._records.get(k)
            if r:
                result.append(r)
        return result

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._record_order) <= keep:
            return 0
        to_remove = self._record_order[:-keep]
        for k in to_remove:
            self._records.pop(k, None)
        self._record_order = (
            self._record_order[-keep:]
        )
        return len(to_remove)

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
            "total_parsed": len(self._records),
            "total_ops": self._total_ops,
            "total_success": self._total_success,
            "total_failed": self._total_failed,
        }
