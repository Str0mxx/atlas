"""ATLAS Agent Fabrikasi modulu.

Yeni agent planlari olusturur, yetenekler ekler, arac baglar ve
Python kaynak kodu uretir. Sablon tabanli iskele kurma ile agent'lari
sistem kayit defterinde yonetir.
"""

import logging
import textwrap
from typing import Any, Optional
from uuid import uuid4

from app.models.selfcode import AgentBlueprint

logger = logging.getLogger(__name__)

# Kategori bazli agent sablonlari
AGENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "monitor": {
        "base_class": "BaseMonitor",
        "capabilities": ["monitoring", "alerting"],
    },
    "analyzer": {
        "base_class": "BaseAgent",
        "capabilities": ["analysis", "reporting"],
    },
    "communicator": {
        "base_class": "BaseAgent",
        "capabilities": ["messaging", "email"],
    },
    "security": {
        "base_class": "BaseAgent",
        "capabilities": ["security", "scanning"],
    },
    "generic": {
        "base_class": "BaseAgent",
        "capabilities": [],
    },
}


class AgentFactory:
    """Agent plani olusturucu ve iskele kurucu.

    Spesifikasyonlardan agent planlari olusturur, yetenekler ve araclar
    baglar, Python sinif kodu uretir ve agent'lari dahili kayit defterinde
    yonetir.

    Attributes:
        auto_register: Olusturulan agent'lar otomatik kaydedilsin mi.
    """

    def __init__(self, auto_register: bool = True) -> None:
        """Yeni AgentFactory olusturur.

        Args:
            auto_register: True ise olusturulan agent'lar otomatik kaydedilir.
        """
        self.auto_register = auto_register
        self._registry: dict[str, AgentBlueprint] = {}
        logger.info(
            "AgentFactory baslatildi (otomatik_kayit=%s)", auto_register
        )

    def create_agent(
        self,
        name: str,
        description: str = "",
        category: str = "generic",
        capabilities: Optional[list[str]] = None,
        tools: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> AgentBlueprint:
        """Spesifikasyonlardan yeni bir AgentBlueprint olusturur.

        Kategoriye uygun sablonu secer, yetenekleri ve araclari ekler.
        auto_register aktifse agent'i kayit defterine kaydeder.

        Args:
            name: Agent adi.
            description: Agent aciklamasi.
            category: Agent kategorisi (monitor, analyzer, communicator, security, generic).
            capabilities: Ek yetenek listesi.
            tools: Baglanacak arac listesi.
            config: Ek yapilandirma.

        Returns:
            Olusturulan agent plani.
        """
        logger.info("Agent olusturuluyor: ad=%s, kategori=%s", name, category)

        # Sablonu sec ve temel plani olustur
        template = self.select_template(category)
        blueprint = AgentBlueprint(
            id=uuid4().hex[:12],
            name=name,
            description=description or f"{name} agent'i.",
            base_class=template["base_class"],
            capabilities=list(template["capabilities"]),
            tools=[],
            auto_register=self.auto_register,
            config=config or {},
        )

        # Ek yetenekleri ekle
        if capabilities:
            blueprint = self.inject_capabilities(blueprint, capabilities)

        # Araclari bagla
        if tools:
            blueprint = self.bind_tools(blueprint, tools)

        # Otomatik kayit
        if self.auto_register:
            self.register_agent(blueprint)

        logger.info(
            "Agent olusturuldu: ad=%s, temel_sinif=%s, yetenek=%d, arac=%d",
            blueprint.name,
            blueprint.base_class,
            len(blueprint.capabilities),
            len(blueprint.tools),
        )
        return blueprint

    def select_template(self, category: str) -> dict[str, Any]:
        """Kategoriye gore en uygun temel sablonu secer.

        Args:
            category: Agent kategorisi (monitor, analyzer, communicator, security, generic).

        Returns:
            Secilen sablon yapilandirmasi (base_class ve capabilities iceren dict).
        """
        template = AGENT_TEMPLATES.get(category)
        if template is None:
            logger.warning(
                "Bilinmeyen kategori '%s', 'generic' sablonuna geri donuluyor",
                category,
            )
            template = AGENT_TEMPLATES["generic"]
        else:
            logger.debug("Sablon secildi: kategori=%s", category)
        return template

    def inject_capabilities(
        self, blueprint: AgentBlueprint, capabilities: list[str]
    ) -> AgentBlueprint:
        """Agent planina yetenek ekler.

        Tekrarlanan yetenekleri onleyerek yalnizca yeni yetenekleri ekler.

        Args:
            blueprint: Hedef agent plani.
            capabilities: Eklenecek yetenek listesi.

        Returns:
            Guncellenenmis agent plani.
        """
        existing = set(blueprint.capabilities)
        added: list[str] = []
        for cap in capabilities:
            if cap not in existing:
                blueprint.capabilities.append(cap)
                existing.add(cap)
                added.append(cap)

        if added:
            logger.debug(
                "Yetenekler eklendi (%s): %s",
                blueprint.name,
                ", ".join(added),
            )
        return blueprint

    def bind_tools(
        self, blueprint: AgentBlueprint, tools: list[str]
    ) -> AgentBlueprint:
        """Agent planina arac baglar.

        Tekrarlanan araclari onleyerek yalnizca yeni araclari ekler.

        Args:
            blueprint: Hedef agent plani.
            tools: Baglanacak arac isimleri.

        Returns:
            Guncellenmis agent plani.
        """
        existing = set(blueprint.tools)
        added: list[str] = []
        for tool in tools:
            if tool not in existing:
                blueprint.tools.append(tool)
                existing.add(tool)
                added.append(tool)

        if added:
            logger.debug(
                "Araclar baglandi (%s): %s",
                blueprint.name,
                ", ".join(added),
            )
        return blueprint

    def generate_code(self, blueprint: AgentBlueprint) -> str:
        """Agent planindan Python sinif kaynak kodu uretir.

        Temel siniftan miras alan, __init__, execute() ve analyze()
        metotlarini iceren eksiksiz bir sinif uretir.

        Args:
            blueprint: Kod uretilecek agent plani.

        Returns:
            Uretilen Python kaynak kodu.
        """
        logger.info("Kod uretiliyor: agent=%s", blueprint.name)
        code = self._build_agent_code(blueprint)
        logger.info(
            "Kod uretimi tamamlandi: agent=%s, satir=%d",
            blueprint.name,
            code.count("\n") + 1,
        )
        return code

    def register_agent(self, blueprint: AgentBlueprint) -> None:
        """Agent'i sistem kayit defterine kaydeder.

        Ayni isimde bir agent zaten varsa uzerine yazar ve uyari loglar.

        Args:
            blueprint: Kaydedilecek agent plani.
        """
        if blueprint.name in self._registry:
            logger.warning(
                "Agent '%s' zaten kayitli, uzerine yazilacak",
                blueprint.name,
            )
        self._registry[blueprint.name] = blueprint
        logger.info("Agent kaydedildi: %s", blueprint.name)

    def unregister_agent(self, name: str) -> bool:
        """Agent'i kayit defterinden siler.

        Args:
            name: Silinecek agent'in adi.

        Returns:
            True eger agent bulunup silindiyse, aksi halde False.
        """
        if name in self._registry:
            del self._registry[name]
            logger.info("Agent kayit silindi: %s", name)
            return True
        logger.warning("Agent bulunamadi, silinemedi: %s", name)
        return False

    def list_agents(self) -> list[AgentBlueprint]:
        """Kayitli tum agent planlarini listeler.

        Returns:
            Kayitli AgentBlueprint nesnelerinin listesi.
        """
        agents = list(self._registry.values())
        logger.debug("Kayitli agent sayisi: %d", len(agents))
        return agents

    def get_agent(self, name: str) -> Optional[AgentBlueprint]:
        """Kayit defterinden belirli bir agent planini getirir.

        Args:
            name: Aranacak agent adi.

        Returns:
            Bulunan AgentBlueprint veya None.
        """
        blueprint = self._registry.get(name)
        if blueprint is None:
            logger.debug("Agent bulunamadi: %s", name)
        return blueprint

    def _build_agent_code(self, blueprint: AgentBlueprint) -> str:
        """Agent planindan Python sinif kodu olusturur.

        Temel siniftan miras alan, uygun docstring ve tip ipuclari
        iceren __init__, execute() ve analyze() metotlarini uretir.

        Args:
            blueprint: Kod olusturulacak agent plani.

        Returns:
            Tam Python sinif kodu dizgesi.
        """
        class_name = self._to_class_name(blueprint.name)
        base = blueprint.base_class
        desc = blueprint.description or f"{class_name} agent'i."
        capabilities_repr = repr(blueprint.capabilities)
        tools_repr = repr(blueprint.tools)

        code = textwrap.dedent(f'''\
            """ATLAS {class_name} modulu.

            Otomatik uretilmis agent sinifi.
            """

            import logging
            from typing import Any, Optional

            logger = logging.getLogger(__name__)


            class {class_name}({base}):
                """{desc}

                Otomatik uretilmis agent. Yetenekler: {", ".join(blueprint.capabilities) or "yok"}.

                Attributes:
                    name: Agent adi.
                    capabilities: Yetenek listesi.
                    tools: Bagli arac listesi.
                """

                def __init__(self, name: str = "{blueprint.name}") -> None:
                    """Yeni {class_name} olusturur.

                    Args:
                        name: Agent adi.
                    """
                    super().__init__(name=name)
                    self.capabilities: list[str] = {capabilities_repr}
                    self.tools: list[str] = {tools_repr}
                    logger.info("{class_name} baslatildi: ad=%s", self.name)

                async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
                    """Verilen gorevi calistirir.

                    Args:
                        task: Gorev parametreleri.

                    Returns:
                        Gorev sonuc sozlugu.
                    """
                    logger.info("{class_name} gorev calistiriliyor: %s", task.get("type", "bilinmeyen"))
                    try:
                        result: dict[str, Any] = {{
                            "agent": self.name,
                            "status": "completed",
                            "task": task,
                        }}
                        return result
                    except Exception as e:
                        logger.error("{class_name} gorev hatasi: %s", e)
                        return {{"agent": self.name, "status": "error", "error": str(e)}}

                async def analyze(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
                    """Veriyi analiz eder ve sonuc dondurur.

                    Args:
                        data: Analiz edilecek veri.

                    Returns:
                        Analiz sonucu veya None (hata durumunda).
                    """
                    logger.info("{class_name} analiz baslatildi")
                    try:
                        analysis: dict[str, Any] = {{
                            "agent": self.name,
                            "capabilities": self.capabilities,
                            "summary": "Analiz tamamlandi",
                            "data_keys": list(data.keys()),
                        }}
                        return analysis
                    except Exception as e:
                        logger.error("{class_name} analiz hatasi: %s", e)
                        return None
        ''')

        return code

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Agent adindan PascalCase sinif adi uretir.

        Alt cizgi ve tire ile ayrilmis kelimeleri PascalCase'e cevirir.
        Eger ad zaten Agent ile bitmiyorsa 'Agent' son eki ekler.

        Args:
            name: Agent adi (orn. 'my_custom_agent' veya 'data-processor').

        Returns:
            PascalCase sinif adi (orn. 'MyCustomAgent', 'DataProcessorAgent').
        """
        # Tire ve alt cizgi ile parcala, her kelimeyi buyuk harfle baslat
        parts = name.replace("-", "_").split("_")
        class_name = "".join(part.capitalize() for part in parts if part)

        # Agent son eki ekle (zaten yoksa)
        if not class_name.endswith("Agent"):
            class_name += "Agent"

        return class_name
