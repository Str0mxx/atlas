"""
CLI Sihirbazi modulu.

Interaktif istemler, adim navigasyonu,
girdi dogrulama, ilerleme goruntusu,
ozet.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CLIWizard:
    """Komut satiri kurulum sihirbazi.

    Attributes:
        _steps: Adim listesi.
        _current: Gecerli adim indeksi.
        _answers: Kullanici cevaplari.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        interactive: bool = True,
        title: str = "ATLAS Setup Wizard",
    ) -> None:
        """Sihirbazi baslatir.

        Args:
            interactive: Interaktif mod.
            title: Sihirbaz basligi.
        """
        self._title = title
        self._interactive = interactive
        self._steps: list[dict] = []
        self._current = 0
        self._answers: dict[str, Any] = {}
        self._completed = False
        self._stats: dict[str, int] = {
            "steps_added": 0,
            "prompts_shown": 0,
            "validations_run": 0,
            "steps_completed": 0,
        }
        logger.info(
            "CLIWizard baslatildi: %s", title
        )

    @property
    def step_count(self) -> int:
        """Toplam adim sayisi."""
        return len(self._steps)

    @property
    def current_step(self) -> int:
        """Gecerli adim indeksi."""
        return self._current

    @property
    def is_completed(self) -> bool:
        """Tamamlandi mi."""
        return self._completed

    def add_step(
        self,
        name: str = "",
        title: str = "",
        description: str = "",
        required: bool = True,
    ) -> dict[str, Any]:
        """Adim ekler.

        Args:
            name: Adim adi (unique).
            title: Adim basligi.
            description: Adim aciklamasi.
            required: Zorunlu mu.

        Returns:
            Ekleme bilgisi.
        """
        try:
            step = {
                "index": len(self._steps),
                "name": name,
                "title": title,
                "description": description,
                "required": required,
                "status": "pending",
            }
            self._steps.append(step)
            self._stats["steps_added"] += 1
            return {
                "added": True,
                "name": name,
                "index": step["index"],
            }
        except Exception as e:
            logger.error("Adim ekleme hatasi: %s", e)
            return {"added": False, "error": str(e)}

    def next_step(self) -> dict[str, Any]:
        """Sonraki adima gider.

        Returns:
            Navigasyon bilgisi.
        """
        try:
            if self._current < len(self._steps) - 1:
                if self._steps:
                    self._steps[self._current]["status"] = "completed"
                    self._stats["steps_completed"] += 1
                self._current += 1
                step = self._steps[self._current]
                step["status"] = "active"
                return {
                    "advanced": True,
                    "step": step["name"],
                    "index": self._current,
                }
            return {
                "advanced": False,
                "error": "son_adimdasiniz",
            }
        except Exception as e:
            logger.error("Adim gecis hatasi: %s", e)
            return {"advanced": False, "error": str(e)}

    def prev_step(self) -> dict[str, Any]:
        """Onceki adima gider.

        Returns:
            Navigasyon bilgisi.
        """
        try:
            if self._current > 0:
                self._steps[self._current]["status"] = "pending"
                self._current -= 1
                step = self._steps[self._current]
                step["status"] = "active"
                return {
                    "back": True,
                    "step": step["name"],
                    "index": self._current,
                }
            return {
                "back": False,
                "error": "ilk_adimdasiniz",
            }
        except Exception as e:
            logger.error("Geri adim hatasi: %s", e)
            return {"back": False, "error": str(e)}

    def skip_step(self) -> dict[str, Any]:
        """Gecerli adimi atlar.

        Returns:
            Atlama bilgisi.
        """
        try:
            if not self._steps:
                return {"skipped": False, "error": "adim_yok"}
            step = self._steps[self._current]
            if step.get("required"):
                return {
                    "skipped": False,
                    "error": "zorunlu_adim_atlanamaz",
                }
            step["status"] = "skipped"
            if self._current < len(self._steps) - 1:
                self._current += 1
            return {"skipped": True, "step": step["name"]}
        except Exception as e:
            logger.error("Atlama hatasi: %s", e)
            return {"skipped": False, "error": str(e)}

    def prompt(
        self,
        question: str = "",
        default: Any = None,
        choices: list | None = None,
        key: str = "",
    ) -> dict[str, Any]:
        """Kullaniciya soru sorar.

        Args:
            question: Soru metni.
            default: Varsayilan deger.
            choices: Secenekler.
            key: Cevap anahtari.

        Returns:
            Cevap bilgisi.
        """
        try:
            self._stats["prompts_shown"] += 1
            # Non-interactive: varsayilan kullan
            value = default
            if choices and default not in choices:
                value = choices[0] if choices else default

            if key:
                self._answers[key] = value

            return {
                "prompted": True,
                "question": question,
                "value": value,
                "key": key,
            }
        except Exception as e:
            logger.error("Istem hatasi: %s", e)
            return {"prompted": False, "error": str(e)}

    def validate_input(
        self,
        value: Any = None,
        validator: Callable | None = None,
        rule: str = "",
    ) -> dict[str, Any]:
        """Girdi dogrular.

        Args:
            value: Dogrulanacak deger.
            validator: Dogrulayici fonksiyon.
            rule: Kural adi.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            self._stats["validations_run"] += 1

            if validator is not None:
                result = validator(value)
                return {
                    "valid": bool(result),
                    "value": value,
                    "rule": rule,
                }

            # Temel kurallar
            if rule == "not_empty":
                valid = value is not None and str(value).strip() != ""
            elif rule == "positive_int":
                valid = isinstance(value, int) and value > 0
            elif rule == "email":
                valid = (
                    isinstance(value, str)
                    and "@" in value
                    and "." in value
                )
            else:
                valid = value is not None

            return {"valid": valid, "value": value, "rule": rule}
        except Exception as e:
            logger.error("Dogrulama hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def display_progress(self) -> dict[str, Any]:
        """Ilerleme gosterir.

        Returns:
            Ilerleme bilgisi.
        """
        try:
            total = len(self._steps)
            completed = sum(
                1 for s in self._steps if s["status"] == "completed"
            )
            percent = (
                int(completed / total * 100) if total > 0 else 0
            )
            return {
                "displayed": True,
                "current": self._current + 1,
                "total": total,
                "completed": completed,
                "percent": percent,
            }
        except Exception as e:
            logger.error("Ilerleme gosterim hatasi: %s", e)
            return {"displayed": False, "error": str(e)}

    def display_summary(
        self, data: dict | None = None
    ) -> dict[str, Any]:
        """Ozet gosterir.

        Args:
            data: Ozetlenecek veri.

        Returns:
            Ozet bilgisi.
        """
        try:
            summary_data = data or self._answers
            return {
                "displayed": True,
                "title": self._title,
                "items": len(summary_data),
                "data": summary_data,
            }
        except Exception as e:
            logger.error("Ozet gosterim hatasi: %s", e)
            return {"displayed": False, "error": str(e)}

    def complete(self) -> dict[str, Any]:
        """Sihirbazi tamamlar.

        Returns:
            Tamamlama bilgisi.
        """
        try:
            # Kalan adimi tamamla
            if self._steps:
                self._steps[self._current]["status"] = "completed"
                self._stats["steps_completed"] += 1
            self._completed = True
            return {
                "completed": True,
                "answers": dict(self._answers),
                "steps_completed": self._stats["steps_completed"],
            }
        except Exception as e:
            logger.error("Tamamlama hatasi: %s", e)
            return {"completed": False, "error": str(e)}

    def reset(self) -> dict[str, Any]:
        """Sihirbazi sifirlar.

        Returns:
            Sifirlama bilgisi.
        """
        try:
            for step in self._steps:
                step["status"] = "pending"
            self._current = 0
            self._answers.clear()
            self._completed = False
            return {"reset": True}
        except Exception as e:
            logger.error("Sifirlama hatasi: %s", e)
            return {"reset": False, "error": str(e)}

    def set_answer(
        self, key: str = "", value: Any = None
    ) -> dict[str, Any]:
        """Cevap ayarlar.

        Args:
            key: Cevap anahtari.
            value: Deger.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            self._answers[key] = value
            return {"set": True, "key": key}
        except Exception as e:
            logger.error("Cevap ayarlama hatasi: %s", e)
            return {"set": False, "error": str(e)}

    def get_answer(self, key: str = "") -> Any:
        """Cevap getirir.

        Args:
            key: Cevap anahtari.

        Returns:
            Cevap degeri.
        """
        return self._answers.get(key)

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            completed = sum(
                1 for s in self._steps if s["status"] == "completed"
            )
            return {
                "retrieved": True,
                "title": self._title,
                "step_count": len(self._steps),
                "current_step": self._current,
                "completed_steps": completed,
                "is_completed": self._completed,
                "answers_count": len(self._answers),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
