"""
Egitim verisi hazirlayici modulu.

Veri formatlama, kalite filtreleme,
tekilleştirme, dogrulama bolumu,
JSONL disa aktarma.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TrainingDataPreparer:
    """Egitim verisi hazirlayici.

    Attributes:
        _datasets: Veri setleri.
        _exports: Disa aktarimlar.
        _stats: Istatistikler.
    """

    FORMATS: list[str] = [
        "chat",
        "completion",
        "instruction",
        "preference",
    ]

    def __init__(
        self,
        min_quality: float = 0.5,
        dedup_threshold: float = 0.95,
    ) -> None:
        """Hazirlayiciyi baslatir.

        Args:
            min_quality: Min kalite esigi.
            dedup_threshold: Tekillesme esigi.
        """
        self._min_quality = min_quality
        self._dedup_threshold = (
            dedup_threshold
        )
        self._datasets: dict[
            str, dict
        ] = {}
        self._exports: list[dict] = []
        self._stats: dict[str, int] = {
            "datasets_created": 0,
            "samples_added": 0,
            "samples_filtered": 0,
            "duplicates_removed": 0,
            "exports_done": 0,
        }
        logger.info(
            "TrainingDataPreparer "
            "baslatildi"
        )

    @property
    def dataset_count(self) -> int:
        """Veri seti sayisi."""
        return len(self._datasets)

    def create_dataset(
        self,
        name: str = "",
        format_type: str = "chat",
        description: str = "",
        validation_split: float = 0.1,
    ) -> dict[str, Any]:
        """Veri seti olusturur.

        Args:
            name: Veri seti adi.
            format_type: Format tipi.
            description: Aciklama.
            validation_split: Dogrulama orani.

        Returns:
            Veri seti bilgisi.
        """
        try:
            did = f"ds_{uuid4()!s:.8}"

            self._datasets[did] = {
                "dataset_id": did,
                "name": name,
                "format_type": format_type,
                "description": description,
                "validation_split": max(
                    0.0,
                    min(0.5, validation_split),
                ),
                "samples": [],
                "hashes": set(),
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "datasets_created"
            ] += 1

            return {
                "dataset_id": did,
                "name": name,
                "format_type": format_type,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def add_sample(
        self,
        dataset_id: str = "",
        input_text: str = "",
        output_text: str = "",
        system_prompt: str = "",
        quality_score: float = 1.0,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Ornek ekler.

        Args:
            dataset_id: Veri seti ID.
            input_text: Giris metni.
            output_text: Cikis metni.
            system_prompt: Sistem promptu.
            quality_score: Kalite puani.
            metadata: Ek veri.

        Returns:
            Ekleme bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "added": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            # Kalite filtresi
            if quality_score < (
                self._min_quality
            ):
                self._stats[
                    "samples_filtered"
                ] += 1
                return {
                    "added": False,
                    "reason": "low_quality",
                    "score": quality_score,
                }

            # Tekillesme
            content = (
                f"{input_text}|{output_text}"
            )
            h = hashlib.md5(
                content.encode()
            ).hexdigest()

            if h in ds["hashes"]:
                self._stats[
                    "duplicates_removed"
                ] += 1
                return {
                    "added": False,
                    "reason": "duplicate",
                }

            ds["hashes"].add(h)

            sample = {
                "input": input_text,
                "output": output_text,
                "system": system_prompt,
                "quality": quality_score,
                "metadata": metadata or {},
                "hash": h,
            }
            ds["samples"].append(sample)

            self._stats[
                "samples_added"
            ] += 1

            return {
                "dataset_id": dataset_id,
                "sample_index": (
                    len(ds["samples"]) - 1
                ),
                "total_samples": len(
                    ds["samples"]
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def add_samples_bulk(
        self,
        dataset_id: str = "",
        samples: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Toplu ornek ekler.

        Args:
            dataset_id: Veri seti ID.
            samples: Ornekler.

        Returns:
            Toplam bilgi.
        """
        try:
            items = samples or []
            added = 0
            filtered = 0
            duped = 0

            for s in items:
                r = self.add_sample(
                    dataset_id=dataset_id,
                    input_text=s.get(
                        "input", ""
                    ),
                    output_text=s.get(
                        "output", ""
                    ),
                    system_prompt=s.get(
                        "system", ""
                    ),
                    quality_score=s.get(
                        "quality", 1.0
                    ),
                    metadata=s.get(
                        "metadata"
                    ),
                )
                if r.get("added"):
                    added += 1
                elif r.get("reason") == (
                    "low_quality"
                ):
                    filtered += 1
                elif r.get("reason") == (
                    "duplicate"
                ):
                    duped += 1

            return {
                "dataset_id": dataset_id,
                "total_submitted": len(
                    items
                ),
                "added": added,
                "filtered": filtered,
                "duplicates": duped,
                "processed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "processed": False,
                "error": str(e),
            }

    def validate_dataset(
        self,
        dataset_id: str = "",
    ) -> dict[str, Any]:
        """Veri setini dogrular.

        Args:
            dataset_id: Veri seti ID.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "validated": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            samples = ds["samples"]
            issues: list[str] = []

            if len(samples) < 10:
                issues.append(
                    "too_few_samples"
                )

            empty_input = sum(
                1
                for s in samples
                if not s["input"].strip()
            )
            if empty_input > 0:
                issues.append(
                    f"{empty_input}_empty_inputs"
                )

            empty_output = sum(
                1
                for s in samples
                if not s["output"].strip()
            )
            if empty_output > 0:
                issues.append(
                    f"{empty_output}_empty_outputs"
                )

            # Kalite dagilimi
            qualities = [
                s["quality"]
                for s in samples
            ]
            avg_q = (
                sum(qualities)
                / len(qualities)
                if qualities
                else 0.0
            )

            return {
                "dataset_id": dataset_id,
                "total_samples": len(
                    samples
                ),
                "avg_quality": round(
                    avg_q, 4
                ),
                "issues": issues,
                "valid": len(issues) == 0,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def split_dataset(
        self,
        dataset_id: str = "",
    ) -> dict[str, Any]:
        """Train/val bolumu yapar.

        Args:
            dataset_id: Veri seti ID.

        Returns:
            Bolum bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "split": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            samples = ds["samples"]
            val_ratio = ds[
                "validation_split"
            ]
            val_count = max(
                1,
                int(
                    len(samples) * val_ratio
                ),
            )

            train = samples[:-val_count]
            val = samples[-val_count:]

            return {
                "dataset_id": dataset_id,
                "train_count": len(train),
                "val_count": len(val),
                "total": len(samples),
                "split": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "split": False,
                "error": str(e),
            }

    def export_jsonl(
        self,
        dataset_id: str = "",
        include_system: bool = True,
    ) -> dict[str, Any]:
        """JSONL olarak disa aktarir.

        Args:
            dataset_id: Veri seti ID.
            include_system: Sistem dahil mi.

        Returns:
            Disa aktarim bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "exported": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            fmt = ds["format_type"]
            lines = []

            for s in ds["samples"]:
                if fmt == "chat":
                    msgs = []
                    if (
                        include_system
                        and s["system"]
                    ):
                        msgs.append({
                            "role": "system",
                            "content": s[
                                "system"
                            ],
                        })
                    msgs.append({
                        "role": "user",
                        "content": s[
                            "input"
                        ],
                    })
                    msgs.append({
                        "role": "assistant",
                        "content": s[
                            "output"
                        ],
                    })
                    line = {
                        "messages": msgs
                    }
                elif fmt == "completion":
                    line = {
                        "prompt": s["input"],
                        "completion": s[
                            "output"
                        ],
                    }
                elif fmt == "instruction":
                    line = {
                        "instruction": s[
                            "input"
                        ],
                        "response": s[
                            "output"
                        ],
                    }
                else:
                    line = {
                        "input": s["input"],
                        "output": s["output"],
                    }

                lines.append(
                    json.dumps(line)
                )

            content = "\n".join(lines)

            export = {
                "dataset_id": dataset_id,
                "format": fmt,
                "lines": len(lines),
                "size_bytes": len(
                    content.encode()
                ),
                "exported_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._exports.append(export)
            self._stats[
                "exports_done"
            ] += 1

            return {
                **export,
                "content": content,
                "exported": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "exported": False,
                "error": str(e),
            }

    def get_dataset_info(
        self,
        dataset_id: str = "",
    ) -> dict[str, Any]:
        """Veri seti bilgisi getirir."""
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "retrieved": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }
            return {
                "dataset_id": dataset_id,
                "name": ds["name"],
                "format_type": ds[
                    "format_type"
                ],
                "total_samples": len(
                    ds["samples"]
                ),
                "validation_split": ds[
                    "validation_split"
                ],
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            total_samples = sum(
                len(d["samples"])
                for d in (
                    self._datasets.values()
                )
            )
            return {
                "total_datasets": len(
                    self._datasets
                ),
                "total_samples": (
                    total_samples
                ),
                "total_exports": len(
                    self._exports
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
