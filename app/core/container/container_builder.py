"""ATLAS Konteyner Olusturucu modulu.

Dockerfile uretimi, multi-stage build,
katman optimizasyonu, temel imaj secimi
ve build argumanlari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContainerBuilder:
    """Konteyner olusturucu.

    Dockerfile olusturur ve build islemlerini yonetir.

    Attributes:
        _builds: Build gecmisi.
        _base_images: Temel imajlar.
    """

    def __init__(self) -> None:
        """Olusturucuyu baslatir."""
        self._builds: list[
            dict[str, Any]
        ] = []
        self._base_images: dict[
            str, dict[str, Any]
        ] = {}
        self._build_args: dict[str, str] = {}
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "builds": 0,
            "failures": 0,
        }

        logger.info(
            "ContainerBuilder baslatildi",
        )

    def register_base_image(
        self,
        name: str,
        tag: str = "latest",
        size_mb: int = 0,
        description: str = "",
    ) -> dict[str, Any]:
        """Temel imaj kaydeder.

        Args:
            name: Imaj adi.
            tag: Etiket.
            size_mb: Boyut (MB).
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        key = f"{name}:{tag}"
        self._base_images[key] = {
            "name": name,
            "tag": tag,
            "size_mb": size_mb,
            "description": description,
            "registered_at": time.time(),
        }

        return {"image": key, "size_mb": size_mb}

    def set_build_arg(
        self,
        key: str,
        value: str,
    ) -> None:
        """Build argumanı ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
        """
        self._build_args[key] = value

    def generate_dockerfile(
        self,
        base_image: str = "python:3.11-slim",
        workdir: str = "/app",
        packages: list[str] | None = None,
        copy_files: list[str] | None = None,
        cmd: str = "",
        expose_port: int | None = None,
        multi_stage: bool = False,
        builder_image: str | None = None,
    ) -> str:
        """Dockerfile uretir.

        Args:
            base_image: Temel imaj.
            workdir: Calisma dizini.
            packages: Paketler.
            copy_files: Kopyalanacak dosyalar.
            cmd: Calistirilacak komut.
            expose_port: Acilacak port.
            multi_stage: Multi-stage mi.
            builder_image: Builder imaji.

        Returns:
            Dockerfile icerigi.
        """
        lines: list[str] = []

        if multi_stage:
            bi = builder_image or base_image
            lines.append(
                f"FROM {bi} AS builder",
            )
            lines.append(f"WORKDIR {workdir}")

            if packages:
                lines.append(
                    "COPY requirements.txt .",
                )
                lines.append(
                    "RUN pip install --no-cache-dir "
                    "-r requirements.txt",
                )

            lines.append("")
            lines.append(
                f"FROM {base_image} AS runtime",
            )
            lines.append(f"WORKDIR {workdir}")
            lines.append(
                f"COPY --from=builder {workdir} "
                f"{workdir}",
            )
        else:
            lines.append(f"FROM {base_image}")
            lines.append(f"WORKDIR {workdir}")

        # Build args
        for k, v in self._build_args.items():
            lines.append(f"ARG {k}={v}")

        # Paketler
        if packages and not multi_stage:
            lines.append(
                "COPY requirements.txt .",
            )
            lines.append(
                "RUN pip install --no-cache-dir "
                "-r requirements.txt",
            )

        # Dosya kopyalama
        for f in (copy_files or ["."]):
            lines.append(f"COPY {f} {workdir}/")

        # Port
        if expose_port:
            lines.append(f"EXPOSE {expose_port}")

        # Komut
        if cmd:
            lines.append(f'CMD {cmd}')

        return "\n".join(lines)

    def build(
        self,
        name: str,
        tag: str = "latest",
        dockerfile: str | None = None,
        context: str = ".",
    ) -> dict[str, Any]:
        """Build islemini baslatir.

        Args:
            name: Imaj adi.
            tag: Etiket.
            dockerfile: Dockerfile icerigi.
            context: Build konteksti.

        Returns:
            Build sonucu.
        """
        self._stats["builds"] += 1

        build_info = {
            "image": f"{name}:{tag}",
            "context": context,
            "status": "success",
            "layers": 0,
            "size_mb": 0,
            "duration_ms": 0,
            "timestamp": time.time(),
        }

        if dockerfile:
            lines = dockerfile.strip().split("\n")
            build_info["layers"] = len([
                l for l in lines
                if l.strip() and
                not l.strip().startswith("#")
            ])
            # Tahmini boyut
            build_info["size_mb"] = (
                build_info["layers"] * 10
            )

        self._builds.append(build_info)
        return build_info

    def optimize_layers(
        self,
        dockerfile: str,
    ) -> dict[str, Any]:
        """Katman optimizasyonu yapar.

        Args:
            dockerfile: Dockerfile icerigi.

        Returns:
            Optimizasyon sonucu.
        """
        lines = dockerfile.strip().split("\n")
        original_layers = len([
            l for l in lines
            if l.strip() and
            not l.strip().startswith("#")
        ])

        # RUN komutlarini birlestir
        run_lines: list[str] = []
        other_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("RUN "):
                run_lines.append(
                    stripped[4:],
                )
            elif stripped:
                other_lines.append(stripped)

        optimized_layers = len(other_lines)
        if run_lines:
            optimized_layers += 1

        return {
            "original_layers": original_layers,
            "optimized_layers": optimized_layers,
            "saved_layers": (
                original_layers - optimized_layers
            ),
            "run_commands_merged": len(run_lines),
        }

    def save_template(
        self,
        name: str,
        base_image: str,
        packages: list[str] | None = None,
        cmd: str = "",
    ) -> dict[str, Any]:
        """Sablon kaydeder.

        Args:
            name: Sablon adi.
            base_image: Temel imaj.
            packages: Paketler.
            cmd: Komut.

        Returns:
            Sablon bilgisi.
        """
        self._templates[name] = {
            "base_image": base_image,
            "packages": packages or [],
            "cmd": cmd,
            "created_at": time.time(),
        }

        return {"name": name, "base_image": base_image}

    def get_template(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Sablon getirir.

        Args:
            name: Sablon adi.

        Returns:
            Sablon bilgisi veya None.
        """
        return self._templates.get(name)

    def select_base_image(
        self,
        language: str,
        minimal: bool = True,
    ) -> str:
        """Dil icin temel imaj secer.

        Args:
            language: Programlama dili.
            minimal: Minimal imaj mi.

        Returns:
            Imaj adi.
        """
        suffix = "-slim" if minimal else ""
        images = {
            "python": f"python:3.11{suffix}",
            "node": f"node:20{suffix}",
            "go": "golang:1.21-alpine",
            "rust": "rust:1.73-slim",
            "java": f"eclipse-temurin:17{suffix}",
        }
        return images.get(
            language.lower(),
            f"{language}:latest",
        )

    def get_builds(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Build gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Build listesi.
        """
        return self._builds[-limit:]

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def build_count(self) -> int:
        """Build sayisi."""
        return self._stats["builds"]

    @property
    def base_image_count(self) -> int:
        """Temel imaj sayisi."""
        return len(self._base_images)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)
