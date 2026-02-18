"""
Few-shot ornek secici modulu.

Ornek secimi, benzerlik esleme,
cesitlilik dengeleme, dinamik secim,
performans takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FewShotSelector:
    """Few-shot ornek secici.

    Attributes:
        _examples: Ornek havuzu.
        _selections: Secim gecmisi.
        _performance: Performans.
        _stats: Istatistikler.
    """

    SELECTION_STRATEGIES: list[str] = [
        "similarity",
        "diversity",
        "performance",
        "random",
        "balanced",
    ]

    def __init__(
        self,
        default_k: int = 3,
    ) -> None:
        """Seciciyi baslatir.

        Args:
            default_k: Varsayilan ornek sayisi.
        """
        self._default_k = default_k
        self._examples: dict[
            str, dict
        ] = {}
        self._selections: list[dict] = []
        self._performance: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "examples_added": 0,
            "selections_made": 0,
            "total_selected": 0,
            "performance_tracked": 0,
        }
        logger.info(
            "FewShotSelector baslatildi"
        )

    @property
    def example_count(self) -> int:
        """Ornek sayisi."""
        return len(self._examples)

    def add_example(
        self,
        input_text: str = "",
        output_text: str = "",
        domain: str = "",
        task_type: str = "",
        tags: list[str] | None = None,
        quality_score: float = 1.0,
    ) -> dict[str, Any]:
        """Ornek ekler.

        Args:
            input_text: Giris metni.
            output_text: Cikis metni.
            domain: Alan.
            task_type: Gorev tipi.
            tags: Etiketler.
            quality_score: Kalite puani.

        Returns:
            Ekleme bilgisi.
        """
        try:
            eid = f"ex_{uuid4()!s:.8}"

            self._examples[eid] = {
                "example_id": eid,
                "input": input_text,
                "output": output_text,
                "domain": domain,
                "task_type": task_type,
                "tags": tags or [],
                "quality_score": max(
                    0.0, min(1.0, quality_score)
                ),
                "usage_count": 0,
                "success_rate": 0.0,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "examples_added"
            ] += 1

            return {
                "example_id": eid,
                "domain": domain,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def select_examples(
        self,
        query: str = "",
        k: int = 0,
        domain: str = "",
        task_type: str = "",
        strategy: str = "balanced",
        exclude_ids: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Ornek secer.

        Args:
            query: Sorgu.
            k: Secilecek sayi.
            domain: Alan filtresi.
            task_type: Gorev filtresi.
            strategy: Secim stratejisi.
            exclude_ids: Haric tutulanlar.

        Returns:
            Secim bilgisi.
        """
        try:
            num = k or self._default_k
            excluded = set(
                exclude_ids or []
            )

            # Filtrele
            candidates = []
            for ex in (
                self._examples.values()
            ):
                if (
                    ex["example_id"]
                    in excluded
                ):
                    continue
                if (
                    domain
                    and ex["domain"] != domain
                ):
                    continue
                if (
                    task_type
                    and ex["task_type"]
                    != task_type
                ):
                    continue
                candidates.append(ex)

            if not candidates:
                return {
                    "examples": [],
                    "count": 0,
                    "selected": True,
                }

            # Strateji uygula
            if strategy == "similarity":
                selected = (
                    self._select_similar(
                        query, candidates, num
                    )
                )
            elif strategy == "diversity":
                selected = (
                    self._select_diverse(
                        candidates, num
                    )
                )
            elif strategy == "performance":
                selected = (
                    self._select_by_perf(
                        candidates, num
                    )
                )
            elif strategy == "balanced":
                selected = (
                    self._select_balanced(
                        query, candidates, num
                    )
                )
            else:
                selected = candidates[:num]

            # Kullanim sayaci
            for ex in selected:
                ex["usage_count"] += 1

            sid = f"sl_{uuid4()!s:.8}"
            self._selections.append({
                "selection_id": sid,
                "query": query,
                "strategy": strategy,
                "count": len(selected),
                "example_ids": [
                    e["example_id"]
                    for e in selected
                ],
                "selected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            self._stats[
                "selections_made"
            ] += 1
            self._stats[
                "total_selected"
            ] += len(selected)

            return {
                "selection_id": sid,
                "examples": [
                    {
                        "example_id": e[
                            "example_id"
                        ],
                        "input": e["input"],
                        "output": e["output"],
                        "domain": e["domain"],
                        "quality_score": e[
                            "quality_score"
                        ],
                    }
                    for e in selected
                ],
                "count": len(selected),
                "strategy": strategy,
                "selected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "selected": False,
                "error": str(e),
            }

    def _select_similar(
        self,
        query: str,
        candidates: list[dict],
        k: int,
    ) -> list[dict]:
        """Benzerlik ile secer."""
        query_words = set(
            query.lower().split()
        )

        scored = []
        for ex in candidates:
            input_words = set(
                ex["input"].lower().split()
            )
            if not query_words:
                overlap = 0.0
            else:
                common = (
                    query_words
                    & input_words
                )
                union = (
                    query_words
                    | input_words
                )
                overlap = (
                    len(common) / len(union)
                    if union
                    else 0.0
                )
            scored.append((overlap, ex))

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )
        return [s[1] for s in scored[:k]]

    def _select_diverse(
        self,
        candidates: list[dict],
        k: int,
    ) -> list[dict]:
        """Cesitlilik ile secer."""
        # Domain cesitliligi
        by_domain: dict[
            str, list[dict]
        ] = {}
        for ex in candidates:
            d = ex["domain"] or "general"
            if d not in by_domain:
                by_domain[d] = []
            by_domain[d].append(ex)

        selected = []
        domains = list(by_domain.keys())
        idx = 0

        while len(selected) < k:
            if not domains:
                break
            domain = domains[
                idx % len(domains)
            ]
            exs = by_domain[domain]
            if exs:
                selected.append(
                    exs.pop(0)
                )
            else:
                domains.remove(domain)
                if not domains:
                    break
                idx = idx % len(domains)
                continue
            idx += 1

        return selected

    def _select_by_perf(
        self,
        candidates: list[dict],
        k: int,
    ) -> list[dict]:
        """Performans ile secer."""
        scored = sorted(
            candidates,
            key=lambda x: (
                x["quality_score"]
                * 0.6
                + x["success_rate"]
                * 0.4
            ),
            reverse=True,
        )
        return scored[:k]

    def _select_balanced(
        self,
        query: str,
        candidates: list[dict],
        k: int,
    ) -> list[dict]:
        """Dengeli secim."""
        query_words = set(
            query.lower().split()
        )

        scored = []
        for ex in candidates:
            input_words = set(
                ex["input"].lower().split()
            )
            union = (
                query_words | input_words
            )
            sim = (
                len(
                    query_words
                    & input_words
                )
                / len(union)
                if union
                else 0.0
            )

            score = (
                sim * 0.4
                + ex["quality_score"] * 0.3
                + ex["success_rate"] * 0.3
            )
            scored.append((score, ex))

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )
        return [s[1] for s in scored[:k]]

    def format_few_shot(
        self,
        examples: list[dict] | None = None,
        task: str = "",
        format_type: str = "qa",
    ) -> dict[str, Any]:
        """Few-shot prompt formatlar.

        Args:
            examples: Ornekler.
            task: Gorev.
            format_type: Format tipi.

        Returns:
            Formatlanmis prompt.
        """
        try:
            exs = examples or []

            if format_type == "qa":
                parts = [
                    f"Q: {e.get('input', '')}"
                    f"\nA: "
                    f"{e.get('output', '')}"
                    for e in exs
                ]
                prompt = (
                    "\n\n".join(parts)
                    + f"\n\nQ: {task}\nA:"
                )
            elif format_type == (
                "instruction"
            ):
                parts = [
                    f"Input: "
                    f"{e.get('input', '')}"
                    f"\nOutput: "
                    f"{e.get('output', '')}"
                    for e in exs
                ]
                prompt = (
                    "\n\n".join(parts)
                    + f"\n\nInput: {task}"
                    + "\nOutput:"
                )
            elif format_type == (
                "conversation"
            ):
                parts = [
                    f"User: "
                    f"{e.get('input', '')}"
                    f"\nAssistant: "
                    f"{e.get('output', '')}"
                    for e in exs
                ]
                prompt = (
                    "\n\n".join(parts)
                    + f"\n\nUser: {task}"
                    + "\nAssistant:"
                )
            else:
                parts = [
                    f"{e.get('input', '')}"
                    f" -> "
                    f"{e.get('output', '')}"
                    for e in exs
                ]
                prompt = (
                    "\n".join(parts)
                    + f"\n{task} ->"
                )

            return {
                "prompt": prompt,
                "example_count": len(exs),
                "format_type": format_type,
                "formatted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "formatted": False,
                "error": str(e),
            }

    def record_performance(
        self,
        example_id: str = "",
        success: bool = True,
        quality_score: float = 0.0,
    ) -> dict[str, Any]:
        """Performans kaydeder.

        Args:
            example_id: Ornek ID.
            success: Basarili mi.
            quality_score: Kalite puani.

        Returns:
            Kayit bilgisi.
        """
        try:
            ex = self._examples.get(
                example_id
            )
            if not ex:
                return {
                    "recorded": False,
                    "error": (
                        "Ornek bulunamadi"
                    ),
                }

            # Performans guncelle
            pid = example_id
            if pid not in self._performance:
                self._performance[pid] = {
                    "total": 0,
                    "successes": 0,
                    "scores": [],
                }

            perf = self._performance[pid]
            perf["total"] += 1
            if success:
                perf["successes"] += 1
            if quality_score > 0:
                perf["scores"].append(
                    quality_score
                )

            # Basari orani guncelle
            ex["success_rate"] = (
                perf["successes"]
                / perf["total"]
            )

            # Kalite puani guncelle
            if perf["scores"]:
                ex["quality_score"] = (
                    sum(perf["scores"])
                    / len(perf["scores"])
                )

            self._stats[
                "performance_tracked"
            ] += 1

            return {
                "example_id": example_id,
                "success_rate": ex[
                    "success_rate"
                ],
                "quality_score": ex[
                    "quality_score"
                ],
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_domain: dict[str, int] = {}
            for ex in (
                self._examples.values()
            ):
                d = (
                    ex["domain"] or "general"
                )
                by_domain[d] = (
                    by_domain.get(d, 0) + 1
                )

            return {
                "total_examples": len(
                    self._examples
                ),
                "total_selections": len(
                    self._selections
                ),
                "by_domain": by_domain,
                "default_k": self._default_k,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
