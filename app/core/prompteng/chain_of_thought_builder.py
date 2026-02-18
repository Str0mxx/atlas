"""
Chain of thought builder modulu.

CoT prompt uretimi, adim adim
muhakeme, self-consistency,
tree of thought, yansitma promptlari.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChainOfThoughtBuilder:
    """Chain of thought olusturucu.

    Attributes:
        _chains: Zincir kayitlari.
        _templates: CoT sablonlari.
        _stats: Istatistikler.
    """

    COT_TYPES: list[str] = [
        "standard",
        "zero_shot",
        "few_shot",
        "self_consistency",
        "tree_of_thought",
        "reflection",
        "step_by_step",
    ]

    def __init__(self) -> None:
        """CoT builder baslatir."""
        self._chains: dict[
            str, dict
        ] = {}
        self._templates: dict[
            str, dict
        ] = {
            "standard": {
                "prefix": (
                    "Let's think step "
                    "by step."
                ),
                "suffix": (
                    "Therefore, the "
                    "answer is:"
                ),
            },
            "zero_shot": {
                "prefix": (
                    "Let's work through "
                    "this step by step:"
                ),
                "suffix": (
                    "Based on this "
                    "reasoning:"
                ),
            },
            "reflection": {
                "prefix": (
                    "Let me think about "
                    "this carefully."
                ),
                "suffix": (
                    "After reflection, "
                    "my conclusion is:"
                ),
            },
        }
        self._stats: dict[str, int] = {
            "chains_built": 0,
            "steps_generated": 0,
            "trees_created": 0,
            "reflections_added": 0,
        }
        logger.info(
            "ChainOfThoughtBuilder "
            "baslatildi"
        )

    @property
    def chain_count(self) -> int:
        """Zincir sayisi."""
        return len(self._chains)

    def build_cot(
        self,
        task: str = "",
        cot_type: str = "standard",
        num_steps: int = 0,
        examples: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """CoT prompt olusturur.

        Args:
            task: Gorev.
            cot_type: CoT tipi.
            num_steps: Adim sayisi.
            examples: Ornekler.

        Returns:
            CoT bilgisi.
        """
        try:
            cid = f"ct_{uuid4()!s:.8}"

            if cot_type == "standard":
                prompt = (
                    self._build_standard(
                        task
                    )
                )
            elif cot_type == "zero_shot":
                prompt = (
                    self._build_zero_shot(
                        task
                    )
                )
            elif cot_type == "few_shot":
                prompt = (
                    self._build_few_shot(
                        task,
                        examples or [],
                    )
                )
            elif cot_type == (
                "self_consistency"
            ):
                prompt = (
                    self
                    ._build_self_consistency(
                        task, num_steps or 3
                    )
                )
            elif cot_type == (
                "tree_of_thought"
            ):
                prompt = (
                    self._build_tree(
                        task,
                        num_steps or 3,
                    )
                )
            elif cot_type == "reflection":
                prompt = (
                    self._build_reflection(
                        task
                    )
                )
            elif cot_type == "step_by_step":
                prompt = (
                    self._build_steps(
                        task,
                        num_steps or 5,
                    )
                )
            else:
                prompt = (
                    self._build_standard(
                        task
                    )
                )

            self._chains[cid] = {
                "chain_id": cid,
                "task": task,
                "cot_type": cot_type,
                "prompt": prompt,
                "steps": num_steps,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "chains_built"
            ] += 1

            return {
                "chain_id": cid,
                "cot_type": cot_type,
                "prompt": prompt,
                "built": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "built": False,
                "error": str(e),
            }

    def _build_standard(
        self,
        task: str,
    ) -> str:
        """Standart CoT."""
        tpl = self._templates["standard"]
        return (
            f"{task}\n\n"
            f"{tpl['prefix']}\n\n"
            f"{tpl['suffix']}"
        )

    def _build_zero_shot(
        self,
        task: str,
    ) -> str:
        """Zero-shot CoT."""
        tpl = self._templates["zero_shot"]
        return (
            f"{task}\n\n"
            f"{tpl['prefix']}\n\n"
            f"{tpl['suffix']}"
        )

    def _build_few_shot(
        self,
        task: str,
        examples: list[dict],
    ) -> str:
        """Few-shot CoT."""
        parts = []
        for ex in examples:
            q = ex.get("question", "")
            r = ex.get("reasoning", "")
            a = ex.get("answer", "")
            parts.append(
                f"Q: {q}\n"
                f"Reasoning: {r}\n"
                f"A: {a}"
            )

        examples_text = "\n\n".join(parts)
        return (
            f"Here are some examples:\n\n"
            f"{examples_text}\n\n"
            f"Now solve this:\n"
            f"Q: {task}\n"
            f"Reasoning:"
        )

    def _build_self_consistency(
        self,
        task: str,
        num_paths: int,
    ) -> str:
        """Self-consistency CoT."""
        paths = "\n".join(
            f"Path {i + 1}: "
            f"[Reason independently]"
            for i in range(num_paths)
        )

        self._stats[
            "steps_generated"
        ] += num_paths

        return (
            f"{task}\n\n"
            f"Generate {num_paths} "
            f"independent reasoning "
            f"paths:\n\n"
            f"{paths}\n\n"
            f"Compare all paths and "
            f"select the most "
            f"consistent answer."
        )

    def _build_tree(
        self,
        task: str,
        breadth: int,
    ) -> str:
        """Tree of thought."""
        branches = "\n".join(
            f"Branch {i + 1}: "
            f"[Explore approach {i + 1}]"
            for i in range(breadth)
        )

        self._stats[
            "trees_created"
        ] += 1

        return (
            f"{task}\n\n"
            f"Explore {breadth} different "
            f"approaches:\n\n"
            f"{branches}\n\n"
            f"Evaluate each branch. "
            f"Prune unpromising ones. "
            f"Deepen the most promising "
            f"path.\n\n"
            f"Final answer based on "
            f"best branch:"
        )

    def _build_reflection(
        self,
        task: str,
    ) -> str:
        """Yansitma promptu."""
        tpl = self._templates["reflection"]

        self._stats[
            "reflections_added"
        ] += 1

        return (
            f"{task}\n\n"
            f"{tpl['prefix']}\n\n"
            f"Initial thought:\n"
            f"[First impression]\n\n"
            f"Wait, let me reconsider:\n"
            f"[Check for errors]\n\n"
            f"After deeper analysis:\n"
            f"[Refined reasoning]\n\n"
            f"{tpl['suffix']}"
        )

    def _build_steps(
        self,
        task: str,
        num_steps: int,
    ) -> str:
        """Adim adim."""
        steps = "\n".join(
            f"Step {i + 1}: "
            f"[Describe step {i + 1}]"
            for i in range(num_steps)
        )

        self._stats[
            "steps_generated"
        ] += num_steps

        return (
            f"{task}\n\n"
            f"Solve this in {num_steps} "
            f"steps:\n\n"
            f"{steps}\n\n"
            f"Conclusion:"
        )

    def add_template(
        self,
        name: str = "",
        prefix: str = "",
        suffix: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """CoT sablonu ekler.

        Args:
            name: Sablon adi.
            prefix: On ek.
            suffix: Son ek.
            description: Aciklama.

        Returns:
            Sablon bilgisi.
        """
        try:
            self._templates[name] = {
                "prefix": prefix,
                "suffix": suffix,
                "description": description,
            }

            return {
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def enhance_with_reflection(
        self,
        prompt: str = "",
    ) -> dict[str, Any]:
        """Yansitma ile zenginlestirir.

        Args:
            prompt: Prompt.

        Returns:
            Zenginlesmis prompt.
        """
        try:
            enhanced = (
                f"{prompt}\n\n"
                f"Before answering, "
                f"consider:\n"
                f"1. What assumptions am I "
                f"making?\n"
                f"2. Could I be wrong "
                f"about anything?\n"
                f"3. What alternative "
                f"perspectives exist?\n"
                f"4. Am I missing any "
                f"important factors?\n\n"
                f"Now, with these "
                f"considerations in mind:"
            )

            self._stats[
                "reflections_added"
            ] += 1

            return {
                "enhanced_prompt": enhanced,
                "enhanced": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "enhanced": False,
                "error": str(e),
            }

    def get_chain(
        self,
        chain_id: str = "",
    ) -> dict[str, Any]:
        """Zinciri getirir."""
        try:
            chain = self._chains.get(
                chain_id
            )
            if not chain:
                return {
                    "retrieved": False,
                    "error": (
                        "Zincir bulunamadi"
                    ),
                }
            return {
                **chain,
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
            by_type: dict[str, int] = {}
            for c in (
                self._chains.values()
            ):
                t = c["cot_type"]
                by_type[t] = (
                    by_type.get(t, 0) + 1
                )

            return {
                "total_chains": len(
                    self._chains
                ),
                "total_templates": len(
                    self._templates
                ),
                "by_type": by_type,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
