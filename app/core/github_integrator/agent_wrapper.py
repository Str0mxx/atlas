"""ATLAS Agent Sarmalayici modulu.

Harici araci ATLAS agent olarak sarmalama,
API adaptor uretimi, giris/cikis esleme,
hata yonetimi ve MasterAgent kaydi.
"""

import logging
from typing import Any

from app.models.github_integrator import (
    RepoAnalysis,
    WrapperConfig,
    WrapperType,
)

logger = logging.getLogger(__name__)


class AgentWrapper:
    """Agent sarmalama sistemi.

    Harici araclari ATLAS agent olarak sarmalar,
    API adaptor uretir ve sisteme kaydeder.

    Attributes:
        _wrappers: Sarmalayici konfigurasyonlari.
        _registered: Kayitli agent'lar.
    """

    def __init__(self) -> None:
        """Agent sarmalayiciyi baslatir."""
        self._wrappers: dict[str, WrapperConfig] = {}
        self._registered: set[str] = set()

        logger.info("AgentWrapper baslatildi")

    def wrap_as_agent(
        self,
        repo_name: str,
        entry_point: str,
        agent_name: str | None = None,
        analysis: RepoAnalysis | None = None,
    ) -> WrapperConfig:
        """Harici araci agent olarak sarmalar.

        Args:
            repo_name: Repo adi.
            entry_point: Giris noktasi (modul veya fonksiyon).
            agent_name: Agent adi.
            analysis: Repo analizi.

        Returns:
            WrapperConfig nesnesi.
        """
        name = agent_name or f"{repo_name}_agent"

        # Giris/cikis esleme olustur
        input_mapping = self._generate_input_mapping(analysis)
        output_mapping = self._generate_output_mapping(analysis)
        error_handlers = self._generate_error_handlers(repo_name)

        config = WrapperConfig(
            repo_name=repo_name,
            wrapper_type=WrapperType.AGENT,
            agent_name=name,
            entry_point=entry_point,
            input_mapping=input_mapping,
            output_mapping=output_mapping,
            error_handlers=error_handlers,
        )

        self._wrappers[name] = config

        logger.info("Agent sarmalandi: %s -> %s", repo_name, name)
        return config

    def wrap_as_tool(
        self,
        repo_name: str,
        entry_point: str,
        tool_name: str | None = None,
    ) -> WrapperConfig:
        """Harici araci tool olarak sarmalar.

        Args:
            repo_name: Repo adi.
            entry_point: Giris noktasi.
            tool_name: Arac adi.

        Returns:
            WrapperConfig nesnesi.
        """
        name = tool_name or f"{repo_name}_tool"

        config = WrapperConfig(
            repo_name=repo_name,
            wrapper_type=WrapperType.TOOL,
            agent_name=name,
            entry_point=entry_point,
            input_mapping={"input": "str", "params": "dict"},
            output_mapping={"result": "Any", "status": "str"},
            error_handlers=[
                f"try: result = {entry_point}(input)",
                "except Exception as e: return error_response(e)",
            ],
        )

        self._wrappers[name] = config
        return config

    def register(self, wrapper_name: str) -> bool:
        """Agent'i sisteme kaydeder.

        Args:
            wrapper_name: Sarmalayici adi.

        Returns:
            Basarili ise True.
        """
        if wrapper_name not in self._wrappers:
            return False

        self._wrappers[wrapper_name].registered = True
        self._registered.add(wrapper_name)

        logger.info("Agent kaydedildi: %s", wrapper_name)
        return True

    def unregister(self, wrapper_name: str) -> bool:
        """Agent kaydi siler.

        Args:
            wrapper_name: Sarmalayici adi.

        Returns:
            Basarili ise True.
        """
        if wrapper_name not in self._wrappers:
            return False

        self._wrappers[wrapper_name].registered = False
        self._registered.discard(wrapper_name)
        return True

    def get_wrapper(self, name: str) -> WrapperConfig | None:
        """Sarmalayici konfigurasyonunu getirir.

        Args:
            name: Sarmalayici adi.

        Returns:
            WrapperConfig veya None.
        """
        return self._wrappers.get(name)

    def list_wrappers(
        self, registered_only: bool = False
    ) -> list[WrapperConfig]:
        """Sarmalayicilari listeler.

        Args:
            registered_only: Sadece kayitlilari getir.

        Returns:
            WrapperConfig listesi.
        """
        if registered_only:
            return [w for w in self._wrappers.values() if w.registered]
        return list(self._wrappers.values())

    def generate_agent_code(self, wrapper_name: str) -> str:
        """Agent kodu uretir.

        Args:
            wrapper_name: Sarmalayici adi.

        Returns:
            Uretilen kod metni.
        """
        config = self._wrappers.get(wrapper_name)
        if not config:
            return ""

        code = f'''"""ATLAS {config.agent_name} - Otomatik uretildi."""

from app.agents.base_agent import BaseAgent

class {self._to_class_name(config.agent_name)}(BaseAgent):
    """Harici arac agent'i: {config.repo_name}."""

    def __init__(self):
        super().__init__(name="{config.agent_name}")
        self._entry = "{config.entry_point}"

    async def execute(self, task):
        """Gorevi calistirir."""
        try:
            # Input mapping
            mapped_input = self._map_input(task)
            # Execute
            result = await self._run(mapped_input)
            # Output mapping
            return self._map_output(result)
        except Exception as e:
            return {{"error": str(e), "agent": "{config.agent_name}"}}
'''
        return code

    def _generate_input_mapping(
        self, analysis: RepoAnalysis | None
    ) -> dict[str, str]:
        """Giris esleme olusturur."""
        mapping = {"task": "str", "parameters": "dict"}

        if analysis and analysis.has_api:
            mapping["endpoint"] = "str"
            mapping["method"] = "str"
            mapping["body"] = "dict"

        return mapping

    def _generate_output_mapping(
        self, analysis: RepoAnalysis | None
    ) -> dict[str, str]:
        """Cikis esleme olusturur."""
        mapping = {"result": "Any", "success": "bool", "error": "str"}

        if analysis and analysis.has_api:
            mapping["status_code"] = "int"
            mapping["response_body"] = "dict"

        return mapping

    def _generate_error_handlers(self, repo_name: str) -> list[str]:
        """Hata isleyiciler olusturur."""
        return [
            "ConnectionError: Baglanti hatasi, yeniden dene",
            "TimeoutError: Zaman asimi, timeout arttir",
            "ValueError: Gecersiz girdi, parametreleri kontrol et",
            f"Exception: {repo_name} genel hata, logla",
        ]

    def _to_class_name(self, name: str) -> str:
        """Sinif adi olusturur."""
        parts = name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts)

    @property
    def wrapper_count(self) -> int:
        """Sarmalayici sayisi."""
        return len(self._wrappers)

    @property
    def registered_count(self) -> int:
        """Kayitli agent sayisi."""
        return len(self._registered)
