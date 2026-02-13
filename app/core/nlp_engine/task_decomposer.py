"""ATLAS Gorev Ayristirma modulu.

Karmasik gorevleri basit alt gorevlere bolme, bagimlilik tespiti,
paralel/seri ayirimi, alt gorev uretimi ve dogrulama kurallari.
"""

import logging
import re
from typing import Any

from app.models.nlp_engine import (
    Intent,
    SubTask,
    TaskDecomposition,
    TaskRelation,
)

logger = logging.getLogger(__name__)

# Karmasiklik anahtar kelimeleri
_COMPLEXITY_KEYWORDS: dict[str, int] = {
    "basit": 1, "simple": 1, "kolay": 2, "easy": 2,
    "orta": 4, "medium": 4, "normal": 4,
    "karmasik": 7, "complex": 7, "zor": 7, "hard": 7,
    "cok karmasik": 9, "very complex": 9, "kritik": 9, "critical": 9,
}

# Paralel calisma isaret kelimeleri
_PARALLEL_MARKERS = ["ayni anda", "paralel", "es zamanli", "simultaneously", "parallel", "concurrently"]

# Sira isaret kelimeleri
_SEQUENTIAL_MARKERS = ["once", "sonra", "ardindan", "first", "then", "after", "before", "next"]


class TaskDecomposer:
    """Gorev ayristirma sistemi.

    Karmasik gorevleri daha kucuk, yonetilebilir alt gorevlere
    boler. Bagimlilik iliskilerini tespit eder ve paralel
    calisabilecek gruplari belirler.

    Attributes:
        _decompositions: Ayristirma sonuclari (id -> TaskDecomposition).
        _max_subtasks: Maksimum alt gorev sayisi.
    """

    def __init__(self, max_subtasks: int = 20) -> None:
        """Gorev ayristirma sistemini baslatir.

        Args:
            max_subtasks: Maksimum alt gorev sayisi.
        """
        self._decompositions: dict[str, TaskDecomposition] = {}
        self._max_subtasks = max_subtasks

        logger.info("TaskDecomposer baslatildi (max_subtasks=%d)", max_subtasks)

    def decompose(self, task_description: str, intent: Intent | None = None) -> TaskDecomposition:
        """Gorevi alt gorevlere ayristirir.

        Dogal dil aciklamasini analiz ederek alt gorevler olusturur.
        've', 'ayrica', virgul gibi ayiricilari kullanir.

        Args:
            task_description: Gorev aciklamasi.
            intent: Iliskili niyet (varsa).

        Returns:
            TaskDecomposition nesnesi.
        """
        parts = self._split_into_parts(task_description)
        subtasks: list[SubTask] = []

        for i, part in enumerate(parts[:self._max_subtasks]):
            part = part.strip()
            if not part:
                continue

            complexity = self._estimate_complexity(part)
            relation = self._detect_relation(part, i, len(parts))
            validation_rules = self._generate_validation_rules(part)

            subtask = SubTask(
                description=part,
                estimated_complexity=complexity,
                relation=relation,
                validation_rules=validation_rules,
            )
            subtasks.append(subtask)

        # Bagimliliklari belirle
        self._identify_dependencies(subtasks)

        # Paralel gruplari olustur
        parallel_groups = self._find_parallel_groups(subtasks)

        total_complexity = sum(st.estimated_complexity for st in subtasks)

        decomposition = TaskDecomposition(
            original_task=task_description,
            subtasks=subtasks,
            total_complexity=total_complexity,
            parallel_groups=parallel_groups,
        )
        self._decompositions[decomposition.id] = decomposition

        logger.info(
            "Gorev ayristirildi: %d alt gorev, toplam karmasiklik=%d, paralel grup=%d",
            len(subtasks), total_complexity, len(parallel_groups),
        )
        return decomposition

    def _split_into_parts(self, text: str) -> list[str]:
        """Metni alt gorevlere boler.

        Virgul, 've', 'ayrica', numarali liste gibi ayiricilari kullanir.

        Args:
            text: Giris metni.

        Returns:
            Parca listesi.
        """
        # Numarali liste kontrolu (1. xxx 2. yyy)
        numbered = re.findall(r"\d+[.)]\s*([^0-9]+?)(?=\d+[.)]|$)", text)
        if len(numbered) >= 2:
            return [p.strip().rstrip(",. ") for p in numbered if p.strip()]

        # Tire ile baslayanlar (- xxx - yyy)
        dashed = re.findall(r"-\s*(.+?)(?=-\s|$)", text)
        if len(dashed) >= 2:
            return [p.strip() for p in dashed if p.strip()]

        # Ayiricilara gore bol
        separators = [" ve ", " ayrica ", " ardindan ", " sonra ", " also ", " then ", " and then "]
        parts = [text]
        for sep in separators:
            new_parts: list[str] = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts

        # Virgul ile bol (ama cok kisa parcalari birlestir)
        final_parts: list[str] = []
        for part in parts:
            comma_parts = [p.strip() for p in part.split(",") if p.strip()]
            if len(comma_parts) > 1 and all(len(p.split()) >= 2 for p in comma_parts):
                final_parts.extend(comma_parts)
            else:
                final_parts.append(part.strip())

        return [p for p in final_parts if p]

    def _estimate_complexity(self, text: str) -> int:
        """Alt gorev karmasikligini tahmin eder.

        Args:
            text: Alt gorev aciklamasi.

        Returns:
            Karmasiklik puani (1-10).
        """
        text_lower = text.lower()

        # Anahtar kelime kontrol
        for keyword, complexity in _COMPLEXITY_KEYWORDS.items():
            if keyword in text_lower:
                return complexity

        # Kelime sayisina gore tahmin
        word_count = len(text.split())
        if word_count <= 3:
            return 2
        elif word_count <= 8:
            return 4
        elif word_count <= 15:
            return 6
        else:
            return 8

    def _detect_relation(self, text: str, index: int, total: int) -> TaskRelation:
        """Gorev iliskisini tespit eder.

        Args:
            text: Alt gorev metni.
            index: Gorev sirasi.
            total: Toplam gorev sayisi.

        Returns:
            Gorev iliskisi.
        """
        text_lower = text.lower()

        for marker in _PARALLEL_MARKERS:
            if marker in text_lower:
                return TaskRelation.PARALLEL

        for marker in _SEQUENTIAL_MARKERS:
            if marker in text_lower:
                return TaskRelation.SEQUENTIAL

        # 'eger', 'if', 'kosul' gibi kelimeler koşullu
        conditional_markers = ["eger", "if", "kosul", "durumunda", "when", "unless"]
        for marker in conditional_markers:
            if marker in text_lower:
                return TaskRelation.CONDITIONAL

        # 'opsiyonel', 'isteğe bağlı'
        optional_markers = ["opsiyonel", "istege bagli", "optional", "if possible"]
        for marker in optional_markers:
            if marker in text_lower:
                return TaskRelation.OPTIONAL

        return TaskRelation.SEQUENTIAL

    def _identify_dependencies(self, subtasks: list[SubTask]) -> None:
        """Alt gorevler arasi bagimliliklari tespit eder.

        Sirasal gorevler onceki goreve bagimli olur.
        Paralel gorevlerin birbirine bagimliligi olmaz.

        Args:
            subtasks: Alt gorev listesi.
        """
        for i, st in enumerate(subtasks):
            if i == 0:
                continue

            if st.relation == TaskRelation.SEQUENTIAL:
                # Onceki sirasal goreve bagimli
                for j in range(i - 1, -1, -1):
                    if subtasks[j].relation != TaskRelation.OPTIONAL:
                        st.dependencies = [subtasks[j].id]
                        break

    def _find_parallel_groups(self, subtasks: list[SubTask]) -> list[list[str]]:
        """Paralel calisabilecek alt gorev gruplarini bulur.

        Args:
            subtasks: Alt gorev listesi.

        Returns:
            Paralel grup listesi (her grup alt gorev ID'leri icerir).
        """
        groups: list[list[str]] = []
        current_group: list[str] = []

        for st in subtasks:
            if st.relation == TaskRelation.PARALLEL:
                current_group.append(st.id)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = []

        if len(current_group) >= 2:
            groups.append(current_group)

        # Bagimlilik olmayan sirasal gorevleri de gruplama
        no_deps = [st.id for st in subtasks if not st.dependencies and st.relation == TaskRelation.SEQUENTIAL]
        if len(no_deps) >= 2:
            groups.append(no_deps)

        return groups

    def _generate_validation_rules(self, text: str) -> list[str]:
        """Alt gorev icin dogrulama kurallari olusturur.

        Args:
            text: Alt gorev aciklamasi.

        Returns:
            Dogrulama kurallari listesi.
        """
        rules: list[str] = []
        text_lower = text.lower()

        if any(w in text_lower for w in ["olustur", "yaz", "create", "build", "add"]):
            rules.append("Cikti dosyasi/nesne mevcut olmali")

        if any(w in text_lower for w in ["test", "dogrula", "kontrol", "verify", "check"]):
            rules.append("Tum testler gecmeli")

        if any(w in text_lower for w in ["sil", "kaldir", "delete", "remove"]):
            rules.append("Hedef nesne artik mevcut olmamali")

        if any(w in text_lower for w in ["guncelle", "degistir", "update", "modify"]):
            rules.append("Degisiklik uygulanmis olmali")

        return rules

    def get_decomposition(self, decomposition_id: str) -> TaskDecomposition | None:
        """Ayristirma sonucunu getirir.

        Args:
            decomposition_id: Ayristirma ID.

        Returns:
            TaskDecomposition nesnesi veya None.
        """
        return self._decompositions.get(decomposition_id)

    def complete_subtask(self, decomposition_id: str, subtask_id: str) -> bool:
        """Alt gorevi tamamlanmis olarak isaretler.

        Args:
            decomposition_id: Ayristirma ID.
            subtask_id: Alt gorev ID.

        Returns:
            Basarili mi.
        """
        decomp = self._decompositions.get(decomposition_id)
        if not decomp:
            return False

        for st in decomp.subtasks:
            if st.id == subtask_id:
                st.completed = True
                return True
        return False

    @property
    def decomposition_count(self) -> int:
        """Toplam ayristirma sayisi."""
        return len(self._decompositions)
