"""
Prompt versiyon kontrol modulu.

Versiyon takibi, degisiklik gecmisi,
fark gorunumu, geri alma, dal yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PromptVersionControl:
    """Prompt versiyon kontrolu.

    Attributes:
        _prompts: Prompt kayitlari.
        _versions: Versiyon gecmisi.
        _branches: Dallar.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Versiyon kontrolu baslatir."""
        self._prompts: dict[
            str, dict
        ] = {}
        self._versions: dict[
            str, list[dict]
        ] = {}
        self._branches: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "prompts_tracked": 0,
            "versions_created": 0,
            "rollbacks_performed": 0,
            "branches_created": 0,
        }
        logger.info(
            "PromptVersionControl "
            "baslatildi"
        )

    @property
    def prompt_count(self) -> int:
        """Takip edilen prompt sayisi."""
        return len(self._prompts)

    def track_prompt(
        self,
        name: str = "",
        content: str = "",
        author: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Promptu takibe alir.

        Args:
            name: Prompt adi.
            content: Icerik.
            author: Yazar.
            description: Aciklama.

        Returns:
            Takip bilgisi.
        """
        try:
            pid = f"pv_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._prompts[pid] = {
                "prompt_id": pid,
                "name": name,
                "current_content": content,
                "current_version": 1,
                "branch": "main",
                "author": author,
                "description": description,
                "created_at": now,
            }

            self._versions[pid] = [
                {
                    "version": 1,
                    "content": content,
                    "author": author,
                    "message": (
                        "Ilk versiyon"
                    ),
                    "branch": "main",
                    "created_at": now,
                }
            ]

            self._stats[
                "prompts_tracked"
            ] += 1
            self._stats[
                "versions_created"
            ] += 1

            return {
                "prompt_id": pid,
                "version": 1,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def commit(
        self,
        prompt_id: str = "",
        content: str = "",
        message: str = "",
        author: str = "",
    ) -> dict[str, Any]:
        """Yeni versiyon kaydeder.

        Args:
            prompt_id: Prompt ID.
            content: Yeni icerik.
            message: Commit mesaji.
            author: Yazar.

        Returns:
            Commit bilgisi.
        """
        try:
            prompt = self._prompts.get(
                prompt_id
            )
            if not prompt:
                return {
                    "committed": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            new_ver = (
                prompt["current_version"]
                + 1
            )
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._versions[
                prompt_id
            ].append({
                "version": new_ver,
                "content": content,
                "author": author,
                "message": message,
                "branch": prompt["branch"],
                "created_at": now,
            })

            prompt[
                "current_content"
            ] = content
            prompt[
                "current_version"
            ] = new_ver

            self._stats[
                "versions_created"
            ] += 1

            return {
                "prompt_id": prompt_id,
                "version": new_ver,
                "committed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "committed": False,
                "error": str(e),
            }

    def get_history(
        self,
        prompt_id: str = "",
    ) -> dict[str, Any]:
        """Versiyon gecmisi getirir.

        Args:
            prompt_id: Prompt ID.

        Returns:
            Gecmis bilgisi.
        """
        try:
            versions = (
                self._versions.get(
                    prompt_id
                )
            )
            if versions is None:
                return {
                    "retrieved": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            history = [
                {
                    "version": v["version"],
                    "author": v["author"],
                    "message": v["message"],
                    "branch": v["branch"],
                    "created_at": v[
                        "created_at"
                    ],
                }
                for v in versions
            ]

            return {
                "prompt_id": prompt_id,
                "history": history,
                "total_versions": len(
                    history
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def diff(
        self,
        prompt_id: str = "",
        version_a: int = 0,
        version_b: int = 0,
    ) -> dict[str, Any]:
        """Fark gorunumu.

        Args:
            prompt_id: Prompt ID.
            version_a: Versiyon A.
            version_b: Versiyon B.

        Returns:
            Fark bilgisi.
        """
        try:
            versions = (
                self._versions.get(
                    prompt_id
                )
            )
            if versions is None:
                return {
                    "diffed": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            content_a = None
            content_b = None
            for v in versions:
                if v["version"] == version_a:
                    content_a = v["content"]
                if v["version"] == version_b:
                    content_b = v["content"]

            if (
                content_a is None
                or content_b is None
            ):
                return {
                    "diffed": False,
                    "error": (
                        "Versiyon bulunamadi"
                    ),
                }

            # Basit diff
            words_a = set(
                content_a.split()
            )
            words_b = set(
                content_b.split()
            )
            added = words_b - words_a
            removed = words_a - words_b

            return {
                "prompt_id": prompt_id,
                "version_a": version_a,
                "version_b": version_b,
                "content_a": content_a,
                "content_b": content_b,
                "words_added": len(added),
                "words_removed": len(
                    removed
                ),
                "changed": (
                    content_a != content_b
                ),
                "diffed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "diffed": False,
                "error": str(e),
            }

    def rollback(
        self,
        prompt_id: str = "",
        target_version: int = 0,
    ) -> dict[str, Any]:
        """Geri alma yapar.

        Args:
            prompt_id: Prompt ID.
            target_version: Hedef versiyon.

        Returns:
            Geri alma bilgisi.
        """
        try:
            prompt = self._prompts.get(
                prompt_id
            )
            if not prompt:
                return {
                    "rolled_back": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            versions = self._versions.get(
                prompt_id, []
            )
            target = None
            for v in versions:
                if (
                    v["version"]
                    == target_version
                ):
                    target = v
                    break

            if not target:
                return {
                    "rolled_back": False,
                    "error": (
                        "Versiyon bulunamadi"
                    ),
                }

            # Geri al (yeni commit olarak)
            new_ver = (
                prompt["current_version"]
                + 1
            )
            now = datetime.now(
                timezone.utc
            ).isoformat()

            versions.append({
                "version": new_ver,
                "content": target[
                    "content"
                ],
                "author": "system",
                "message": (
                    f"v{target_version}'a "
                    f"geri alma"
                ),
                "branch": prompt["branch"],
                "created_at": now,
            })

            prompt["current_content"] = (
                target["content"]
            )
            prompt[
                "current_version"
            ] = new_ver

            self._stats[
                "rollbacks_performed"
            ] += 1
            self._stats[
                "versions_created"
            ] += 1

            return {
                "prompt_id": prompt_id,
                "rolled_back_to": (
                    target_version
                ),
                "new_version": new_ver,
                "rolled_back": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rolled_back": False,
                "error": str(e),
            }

    def create_branch(
        self,
        prompt_id: str = "",
        branch_name: str = "",
        from_version: int = 0,
    ) -> dict[str, Any]:
        """Dal olusturur.

        Args:
            prompt_id: Prompt ID.
            branch_name: Dal adi.
            from_version: Kaynak versiyon.

        Returns:
            Dal bilgisi.
        """
        try:
            versions = (
                self._versions.get(
                    prompt_id
                )
            )
            if versions is None:
                return {
                    "created": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            # Kaynak versiyon bul
            source = None
            for v in versions:
                if (
                    v["version"]
                    == from_version
                ):
                    source = v
                    break

            if not source and from_version:
                return {
                    "created": False,
                    "error": (
                        "Versiyon bulunamadi"
                    ),
                }

            if not source:
                source = versions[-1]

            bid = (
                f"{prompt_id}:"
                f"{branch_name}"
            )
            self._branches[bid] = {
                "branch_id": bid,
                "prompt_id": prompt_id,
                "branch_name": branch_name,
                "from_version": source[
                    "version"
                ],
                "content": source[
                    "content"
                ],
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "branches_created"
            ] += 1

            return {
                "branch_id": bid,
                "branch_name": branch_name,
                "from_version": source[
                    "version"
                ],
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_prompts": len(
                    self._prompts
                ),
                "total_versions": sum(
                    len(v)
                    for v in (
                        self._versions
                        .values()
                    )
                ),
                "total_branches": len(
                    self._branches
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
