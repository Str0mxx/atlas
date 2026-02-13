"""ATLAS gorev analiz modulu.

Gorev tanimi analiz ederek gerekli arac/yetkinlikleri belirler,
mevcut/eksik araclari kontrol eder ve yetenek eksikliklerini raporlar.
"""

import importlib
import logging
import shutil
from typing import Any

from app.models.bootstrap import (
    GapSeverity,
    SkillGap,
    TaskAnalysis,
    ToolRequirement,
)

logger = logging.getLogger(__name__)

# Anahtar kelime -> gerekli araclar eslesmesi
TASK_TOOL_MAP: dict[str, list[str]] = {
    "web_scraping": ["playwright", "beautifulsoup4", "httpx"],
    "scraping": ["playwright", "beautifulsoup4", "httpx"],
    "email": ["google-api-python-client"],
    "ssh": ["paramiko"],
    "database": ["sqlalchemy", "asyncpg"],
    "docker": ["docker"],
    "image": ["pillow"],
    "pdf": ["reportlab"],
    "excel": ["openpyxl"],
    "api": ["httpx", "fastapi"],
    "ml": ["numpy", "scipy"],
    "nlp": ["langchain", "anthropic"],
    "monitoring": ["psutil"],
    "telegram": ["python-telegram-bot"],
    "redis": ["redis"],
    "vector": ["qdrant-client"],
}

# Kritik araclar — eksikliginde gorev gerceklestirilemez
CRITICAL_TOOLS = {"sqlalchemy", "asyncpg", "httpx", "fastapi", "paramiko"}

# Kurulum onerileri
INSTALL_SUGGESTIONS: dict[str, str] = {
    "playwright": "pip install playwright && playwright install",
    "beautifulsoup4": "pip install beautifulsoup4",
    "httpx": "pip install httpx",
    "paramiko": "pip install paramiko",
    "sqlalchemy": "pip install sqlalchemy",
    "asyncpg": "pip install asyncpg",
    "docker": "pip install docker (veya sistem Docker kurulumu)",
    "pillow": "pip install Pillow",
    "reportlab": "pip install reportlab",
    "openpyxl": "pip install openpyxl",
    "fastapi": "pip install fastapi",
    "numpy": "pip install numpy",
    "scipy": "pip install scipy",
    "langchain": "pip install langchain",
    "anthropic": "pip install anthropic",
    "psutil": "pip install psutil",
    "google-api-python-client": "pip install google-api-python-client",
    "python-telegram-bot": "pip install python-telegram-bot",
    "redis": "pip install redis",
    "qdrant-client": "pip install qdrant-client",
}


class TaskAnalyzer:
    """Gorev analiz sinifi.

    Gorev aciklamasindan gerekli araclari cikarir,
    mevcut araclari kontrol eder ve eksiklikleri raporlar.

    Attributes:
        tool_map: Anahtar kelime -> arac eslesmesi.
    """

    def __init__(
        self,
        tool_map: dict[str, list[str]] | None = None,
    ) -> None:
        """TaskAnalyzer baslatir.

        Args:
            tool_map: Ozel anahtar kelime -> arac eslesmesi. None ise TASK_TOOL_MAP kullanilir.
        """
        self.tool_map = tool_map or dict(TASK_TOOL_MAP)
        logger.info(
            "TaskAnalyzer olusturuldu (kategori=%d)", len(self.tool_map)
        )

    async def analyze(
        self,
        task_description: str,
    ) -> TaskAnalysis:
        """Gorevi analiz eder, gerekli araclari belirler.

        Args:
            task_description: Gorev aciklamasi.

        Returns:
            Gorev analiz sonucu.
        """
        requirements = self.extract_requirements(task_description)
        requirements = await self.check_availability(requirements)

        available = [r.name for r in requirements if r.available]
        missing = [r.name for r in requirements if not r.available]
        gaps = self.identify_skill_gaps(missing)

        feasible = not any(
            m in CRITICAL_TOOLS for m in missing
        )
        confidence = 1.0 if not missing else max(0.1, 1.0 - len(missing) * 0.15)

        analysis = TaskAnalysis(
            task_description=task_description,
            required_tools=requirements,
            available_tools=available,
            missing_tools=missing,
            skill_gaps=gaps,
            feasible=feasible,
            confidence=round(confidence, 2),
        )
        logger.info(
            "Gorev analizi tamamlandi: gerekli=%d, mevcut=%d, eksik=%d",
            len(requirements),
            len(available),
            len(missing),
        )
        return analysis

    def extract_requirements(
        self,
        task_description: str,
    ) -> list[ToolRequirement]:
        """Gorev aciklamasindan gerekli araclari cikarir.

        Args:
            task_description: Gorev aciklamasi.

        Returns:
            Gerekli araclar listesi.
        """
        matched_keywords = self._match_keywords(task_description)
        seen: set[str] = set()
        requirements: list[ToolRequirement] = []

        for keyword in matched_keywords:
            tools = self.tool_map.get(keyword, [])
            for tool in tools:
                if tool not in seen:
                    seen.add(tool)
                    suggestion = INSTALL_SUGGESTIONS.get(tool, f"pip install {tool}")
                    requirements.append(
                        ToolRequirement(
                            name=tool,
                            category=keyword,
                            install_suggestion=suggestion,
                        )
                    )

        return requirements

    async def check_availability(
        self,
        requirements: list[ToolRequirement],
    ) -> list[ToolRequirement]:
        """Araclarin mevcutlugunu kontrol eder.

        Args:
            requirements: Kontrol edilecek araclar.

        Returns:
            Guncellenmis arac listesi.
        """
        for req in requirements:
            is_python = await self._check_python_package(req.name)
            is_system = await self._check_system_tool(req.name)
            req.available = is_python or is_system
        return requirements

    def identify_skill_gaps(
        self,
        missing_tools: list[str],
    ) -> list[SkillGap]:
        """Eksik araclardan yetenek eksikliklerini cikarir.

        Args:
            missing_tools: Eksik arac listesi.

        Returns:
            Yetenek eksiklikleri.
        """
        gaps: list[SkillGap] = []
        for tool in missing_tools:
            severity = (
                GapSeverity.CRITICAL
                if tool in CRITICAL_TOOLS
                else GapSeverity.MEDIUM
            )
            suggestion = INSTALL_SUGGESTIONS.get(tool, f"pip install {tool}")
            gaps.append(
                SkillGap(
                    capability=tool,
                    severity=severity,
                    description=f"{tool} araci eksik",
                    resolution_options=[suggestion],
                )
            )
        return gaps

    def suggest_installations(
        self,
        missing_tools: list[str],
    ) -> dict[str, str]:
        """Eksik araclar icin kurulum onerileri uretir.

        Args:
            missing_tools: Eksik arac listesi.

        Returns:
            Arac -> kurulum komutu eslesmesi.
        """
        return {
            tool: INSTALL_SUGGESTIONS.get(tool, f"pip install {tool}")
            for tool in missing_tools
        }

    def _match_keywords(
        self,
        text: str,
    ) -> list[str]:
        """Metinden anahtar kelimeleri eslestirir.

        Args:
            text: Aranacak metin.

        Returns:
            Eslesen anahtar kelimeler.
        """
        text_lower = text.lower()
        matched: list[str] = []
        for keyword in self.tool_map:
            if keyword in text_lower:
                matched.append(keyword)
        return matched

    async def _check_python_package(
        self,
        name: str,
    ) -> bool:
        """Python paketinin yuklu olup olmadigini kontrol eder.

        Args:
            name: Paket adi.

        Returns:
            Yuklu mu.
        """
        # PyPI paket adlarindaki tire/alt cizgi normalizasyonu
        normalized = name.replace("-", "_").replace(".", "_")
        try:
            importlib.import_module(normalized)
            return True
        except ImportError:
            # Bazi paketler farkli isimle import edilir
            try:
                importlib.import_module(name)
                return True
            except ImportError:
                return False

    async def _check_system_tool(
        self,
        name: str,
    ) -> bool:
        """Sistem aracinin yuklu olup olmadigini kontrol eder.

        Args:
            name: Arac adi.

        Returns:
            Yuklu mu.
        """
        return shutil.which(name) is not None
