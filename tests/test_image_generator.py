"""ImageGenerator unit testleri.

OpenAI DALL-E gorsel uretici davranislari mock'larla test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.image_generator import ImageGenerator, ImageResult


# === Fixture'lar ===


@pytest.fixture
def mock_settings():
    """Test icin settings mock'u."""
    with patch("app.tools.image_generator.settings") as mock:
        mock.openai_api_key = MagicMock()
        mock.openai_api_key.get_secret_value.return_value = "test-openai-key"
        yield mock


@pytest.fixture
def generator(mock_settings) -> ImageGenerator:
    """Yapilandirilmis ImageGenerator."""
    return ImageGenerator()


def _make_image_response(
    url: str = "https://example.com/image.png",
    revised_prompt: str = "A revised prompt",
) -> MagicMock:
    """Test icin OpenAI gorsel yaniti olusturur."""
    response = MagicMock()
    image_data = MagicMock()
    image_data.url = url
    image_data.revised_prompt = revised_prompt
    response.data = [image_data]
    return response


# === Init testleri ===


class TestImageGeneratorInit:
    """ImageGenerator baslatma testleri."""

    def test_default_config(self, mock_settings) -> None:
        """Varsayilan yapilandirma."""
        gen = ImageGenerator()
        assert gen.default_model == "dall-e-3"
        assert gen.default_size == "1024x1024"
        assert gen.default_quality == "standard"
        assert gen.default_style == "vivid"
        assert gen._client is None

    def test_custom_config(self, mock_settings) -> None:
        """Ozel yapilandirma."""
        gen = ImageGenerator(
            default_model="dall-e-2",
            default_size="512x512",
            default_quality="hd",
            default_style="natural",
        )
        assert gen.default_model == "dall-e-2"
        assert gen.default_size == "512x512"
        assert gen.default_quality == "hd"
        assert gen.default_style == "natural"


# === Client testleri ===


class TestGetClient:
    """OpenAI istemci baslatma testleri."""

    @patch("app.tools.image_generator._OPENAI_AVAILABLE", True)
    @patch("app.tools.image_generator.AsyncOpenAI")
    def test_client_created(
        self, mock_openai_cls, generator,
    ) -> None:
        """AsyncOpenAI istemcisi olusturulur."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        result = generator._get_client()

        assert result is mock_client
        mock_openai_cls.assert_called_once_with(api_key="test-openai-key")

    @patch("app.tools.image_generator._OPENAI_AVAILABLE", True)
    @patch("app.tools.image_generator.AsyncOpenAI")
    def test_client_cached(
        self, mock_openai_cls, generator,
    ) -> None:
        """Client ikinci cagirimda cache'ten gelir."""
        mock_openai_cls.return_value = MagicMock()

        generator._get_client()
        generator._get_client()

        assert mock_openai_cls.call_count == 1

    @patch("app.tools.image_generator._OPENAI_AVAILABLE", False)
    def test_client_not_available(self, generator) -> None:
        """openai kurulu degilse RuntimeError."""
        with pytest.raises(RuntimeError, match="openai"):
            generator._get_client()

    def test_missing_api_key(self, mock_settings) -> None:
        """API key yoksa ValueError."""
        mock_settings.openai_api_key.get_secret_value.return_value = ""
        gen = ImageGenerator()

        with patch("app.tools.image_generator._OPENAI_AVAILABLE", True):
            with pytest.raises(ValueError, match="API key"):
                gen._get_client()


# === Generate testleri ===


class TestGenerate:
    """Gorsel uretme testleri."""

    @pytest.mark.asyncio
    async def test_generate_success(self, generator) -> None:
        """Basarili gorsel uretimi."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            return_value=_make_image_response(
                url="https://cdn.example.com/generated.png",
                revised_prompt="A beautiful revised prompt",
            ),
        )
        generator._client = mock_client

        result = await generator.generate("A modern logo for ATLAS")

        assert isinstance(result, ImageResult)
        assert result.success is True
        assert result.url == "https://cdn.example.com/generated.png"
        assert result.revised_prompt == "A beautiful revised prompt"
        assert result.original_prompt == "A modern logo for ATLAS"
        assert result.model == "dall-e-3"
        assert result.size == "1024x1024"

    @pytest.mark.asyncio
    async def test_generate_custom_params(self, generator) -> None:
        """Ozel parametrelerle gorsel uretimi."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            return_value=_make_image_response(),
        )
        generator._client = mock_client

        await generator.generate(
            "Test prompt",
            size="1792x1024",
            quality="hd",
            style="natural",
            model="dall-e-3",
        )

        call_kwargs = mock_client.images.generate.call_args[1]
        assert call_kwargs["size"] == "1792x1024"
        assert call_kwargs["quality"] == "hd"
        assert call_kwargs["style"] == "natural"
        assert call_kwargs["model"] == "dall-e-3"

    @pytest.mark.asyncio
    async def test_generate_error(self, generator) -> None:
        """Gorsel uretim hatasi."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            side_effect=Exception("Rate limit exceeded"),
        )
        generator._client = mock_client

        result = await generator.generate("Test prompt")

        assert result.success is False
        assert "Rate limit" in result.error
        assert result.original_prompt == "Test prompt"


# === GenerateWithRetry testleri ===


class TestGenerateWithRetry:
    """Retry mantigi ile gorsel uretme testleri."""

    @pytest.mark.asyncio
    async def test_retry_success_first_try(self, generator) -> None:
        """Ilk denemede basari."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            return_value=_make_image_response(),
        )
        generator._client = mock_client

        result = await generator.generate_with_retry(
            "Test prompt", max_retries=3, retry_delay=0.01,
        )

        assert result.success is True
        assert mock_client.images.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_second_try(self, generator) -> None:
        """Ikinci denemede basari."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            side_effect=[
                Exception("Temporary error"),
                _make_image_response(),
            ],
        )
        generator._client = mock_client

        result = await generator.generate_with_retry(
            "Test prompt", max_retries=3, retry_delay=0.01,
        )

        assert result.success is True
        assert mock_client.images.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_all_failed(self, generator) -> None:
        """Tum denemeler basarisiz."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            side_effect=Exception("Persistent error"),
        )
        generator._client = mock_client

        result = await generator.generate_with_retry(
            "Test prompt", max_retries=2, retry_delay=0.01,
        )

        assert result.success is False
        assert mock_client.images.generate.call_count == 2


# === GenerateVariations testleri ===


class TestGenerateVariations:
    """Varyasyon uretme testleri."""

    @pytest.mark.asyncio
    async def test_variations_success(self, generator) -> None:
        """Basarili varyasyon uretimi."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(
            return_value=_make_image_response(),
        )
        generator._client = mock_client

        results = await generator.generate_variations(
            "Logo design", count=3,
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(isinstance(r, ImageResult) for r in results)

    @pytest.mark.asyncio
    async def test_variations_partial_failure(self, generator) -> None:
        """Kismi basarisiz varyasyon."""
        mock_client = AsyncMock()
        call_count = 0

        async def mock_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("One failed")
            return _make_image_response()

        mock_client.images.generate = mock_generate
        generator._client = mock_client

        results = await generator.generate_variations(
            "Logo design", count=3,
        )

        assert len(results) == 3
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        assert len(successful) == 2
        assert len(failed) == 1


# === ImageResult modeli testleri ===


class TestImageResult:
    """ImageResult model testleri."""

    def test_default_values(self) -> None:
        """Varsayilan degerler."""
        result = ImageResult()
        assert result.url == ""
        assert result.success is True
        assert result.error == ""

    def test_error_result(self) -> None:
        """Hata iceren sonuc."""
        result = ImageResult(
            success=False,
            error="API error",
            original_prompt="test",
        )
        assert result.success is False
        assert result.error == "API error"
