"""ATLAS AI gorsel uretim modulu.

OpenAI DALL-E API ile gorsel uretimi saglayan
yeniden kullanilabilir arac sinifi.

CreativeAgent bu sinifi kullanarak gorsel uretimi
gerceklestirebilir. Bagimsiz olarak da kullanilabilir.
"""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("atlas.tools.image_generator")

# OpenAI opsiyonel import
_OPENAI_AVAILABLE = False
try:
    from openai import AsyncOpenAI

    _OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment, misc]
    logger.info("openai kurulu degil, ImageGenerator kullanilamaz")


class ImageResult(BaseModel):
    """Gorsel uretim sonucu.

    Attributes:
        url: Uretilen gorselin URL'i.
        revised_prompt: API tarafindan duzeltilmis prompt.
        original_prompt: Kullanicinin girdigi orijinal prompt.
        size: Gorsel boyutu (orn: 1024x1024).
        model: Kullanilan model (orn: dall-e-3).
        success: Uretim basarili mi.
        error: Hata mesaji (basarisizsa).
    """

    url: str = ""
    revised_prompt: str = ""
    original_prompt: str = ""
    size: str = ""
    model: str = ""
    success: bool = True
    error: str = ""


class ImageGenerator:
    """OpenAI DALL-E gorsel uretici.

    DALL-E API ile gorsel uretimi saglar.
    Lazy initialization ile OpenAI istemcisini baslatir.

    Kullanim:
        generator = ImageGenerator()
        result = await generator.generate("A modern logo for ATLAS")

    Attributes:
        default_model: Varsayilan model (dall-e-3).
        default_size: Varsayilan boyut (1024x1024).
        default_quality: Varsayilan kalite (standard).
        default_style: Varsayilan stil (vivid).
    """

    def __init__(
        self,
        default_model: str = "dall-e-3",
        default_size: str = "1024x1024",
        default_quality: str = "standard",
        default_style: str = "vivid",
    ) -> None:
        """ImageGenerator'i baslatir. OpenAI istemcisi lazy yuklenir.

        Args:
            default_model: Varsayilan gorsel uretim modeli.
            default_size: Varsayilan gorsel boyutu.
            default_quality: Varsayilan gorsel kalitesi.
            default_style: Varsayilan gorsel stili.
        """
        self._client: Any | None = None
        self.default_model = default_model
        self.default_size = default_size
        self.default_quality = default_quality
        self.default_style = default_style

    def _get_client(self) -> Any:
        """OpenAI istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis AsyncOpenAI istemcisi.

        Raises:
            RuntimeError: openai kutuphanesi kurulu degilse.
            ValueError: OpenAI API key yapilandirilmamissa.
        """
        if self._client is not None:
            return self._client

        if not _OPENAI_AVAILABLE:
            raise RuntimeError(
                "openai kutuphanesi kurulu degil. "
                "Kurmak icin: pip install openai"
            )

        api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError("OpenAI API key yapilandirilmamis.")

        self._client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI istemcisi baslatildi")
        return self._client

    async def generate(
        self,
        prompt: str,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        model: str | None = None,
    ) -> ImageResult:
        """DALL-E ile gorsel uretir.

        Args:
            prompt: Gorsel aciklamasi.
            size: Gorsel boyutu (orn: 1024x1024, 1792x1024).
            quality: Gorsel kalitesi (standard, hd).
            style: Gorsel stili (vivid, natural).
            model: Kullanilacak model (dall-e-2, dall-e-3).

        Returns:
            Uretim sonucunu iceren ImageResult.
        """
        used_model = model or self.default_model
        used_size = size or self.default_size
        used_quality = quality or self.default_quality
        used_style = style or self.default_style

        try:
            client = self._get_client()

            response = await client.images.generate(
                model=used_model,
                prompt=prompt,
                size=used_size,
                quality=used_quality,
                style=used_style,
                n=1,
            )

            image_data = response.data[0]

            logger.info(
                "Gorsel uretildi: model=%s, size=%s, prompt=%s",
                used_model, used_size, prompt[:80],
            )

            return ImageResult(
                url=image_data.url or "",
                revised_prompt=getattr(image_data, "revised_prompt", "") or "",
                original_prompt=prompt,
                size=used_size,
                model=used_model,
                success=True,
            )
        except Exception as exc:
            logger.error("Gorsel uretim hatasi: %s", exc)
            return ImageResult(
                original_prompt=prompt,
                size=used_size,
                model=used_model,
                success=False,
                error=str(exc),
            )

    async def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        **kwargs: Any,
    ) -> ImageResult:
        """Retry mantigi ile gorsel uretir.

        Basarisiz denemelerde artan bekleme suresi ile tekrar dener.

        Args:
            prompt: Gorsel aciklamasi.
            max_retries: Maksimum deneme sayisi.
            retry_delay: Ilk bekleme suresi (saniye).
            **kwargs: generate() icin ek parametreler.

        Returns:
            Uretim sonucunu iceren ImageResult.
        """
        last_result: ImageResult | None = None

        for attempt in range(max_retries):
            result = await self.generate(prompt, **kwargs)

            if result.success:
                return result

            last_result = result
            if attempt < max_retries - 1:
                wait = retry_delay * (2 ** attempt)
                logger.warning(
                    "Gorsel uretim denemesi %d/%d basarisiz, %ds bekleniyor: %s",
                    attempt + 1, max_retries, wait, result.error,
                )
                await asyncio.sleep(wait)

        logger.error(
            "Gorsel uretim %d denemede basarisiz: %s",
            max_retries, prompt[:80],
        )
        return last_result or ImageResult(
            original_prompt=prompt,
            success=False,
            error=f"{max_retries} deneme basarisiz",
        )

    async def generate_variations(
        self,
        prompt: str,
        count: int = 3,
        **kwargs: Any,
    ) -> list[ImageResult]:
        """Bir prompt icin birden fazla gorsel varyasyonu uretir.

        Her varyasyon ayri bir API cagrisi ile olusturulur.

        Args:
            prompt: Gorsel aciklamasi.
            count: Uretilecek varyasyon sayisi.
            **kwargs: generate() icin ek parametreler.

        Returns:
            ImageResult listesi.
        """
        tasks = [
            self.generate(prompt, **kwargs)
            for _ in range(count)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        image_results: list[ImageResult] = []
        for r in results:
            if isinstance(r, Exception):
                image_results.append(ImageResult(
                    original_prompt=prompt,
                    success=False,
                    error=str(r),
                ))
            else:
                image_results.append(r)

        logger.info(
            "Gorsel varyasyonlari uretildi: %d/%d basarili",
            sum(1 for r in image_results if r.success),
            count,
        )
        return image_results
