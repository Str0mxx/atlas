"""ATLAS Temporal Planner modulu.

Zamansal planlama: deadline kisitlari, sure tahmini,
zamanlama optimizasyonu ve kritik yol analizi.
"""

import logging
from typing import Any

from app.models.planning import (
    ConstraintType,
    ScheduleEntry,
    ScheduleResult,
    TemporalConstraint,
)

logger = logging.getLogger(__name__)


class _TaskNode:
    """Zamanlama grafigi icin dahili gorev dugumu."""

    __slots__ = (
        "task_id",
        "task_name",
        "duration",
        "earliest_start",
        "earliest_finish",
        "latest_start",
        "latest_finish",
        "predecessors",
        "successors",
    )

    def __init__(self, task_id: str, task_name: str, duration: float) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.duration = duration
        self.earliest_start: float = 0.0
        self.earliest_finish: float = 0.0
        self.latest_start: float = float("inf")
        self.latest_finish: float = float("inf")
        self.predecessors: list[str] = []
        self.successors: list[str] = []


class TemporalPlanner:
    """Zamansal planlayici.

    Deadline kisitlari, sure tahmini, zamanlama optimizasyonu
    ve kritik yol analizi (CPM) saglar.

    Attributes:
        tasks: Gorev bilgileri (id -> {name, duration}).
        constraints: Zamansal kisitlar.
        dependencies: Bagimliliklar (gorev_id -> [oncel_gorev_id]).
    """

    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.constraints: list[TemporalConstraint] = []
        self.dependencies: dict[str, list[str]] = {}

    def add_task(
        self,
        task_id: str,
        name: str,
        duration: float,
        predecessors: list[str] | None = None,
    ) -> None:
        """Gorev ekler.

        Args:
            task_id: Gorev ID.
            name: Gorev adi.
            duration: Sure (saniye).
            predecessors: Oncel gorev ID listesi.
        """
        self.tasks[task_id] = {"name": name, "duration": duration}
        if predecessors:
            self.dependencies[task_id] = list(predecessors)
        else:
            self.dependencies.setdefault(task_id, [])

    def add_constraint(self, constraint: TemporalConstraint) -> None:
        """Zamansal kisit ekler.

        Args:
            constraint: Eklenecek kisit.
        """
        self.constraints.append(constraint)

        # DEPENDENCY kisiti bagimlilik olarak da ekle
        if (
            constraint.constraint_type == ConstraintType.DEPENDENCY
            and constraint.reference_task_id
        ):
            deps = self.dependencies.setdefault(constraint.task_id, [])
            if constraint.reference_task_id not in deps:
                deps.append(constraint.reference_task_id)

    def _topological_sort(self, nodes: dict[str, _TaskNode]) -> list[str] | None:
        """Topolojik siralama (Kahn algoritmasi).

        Args:
            nodes: Gorev dugumleri.

        Returns:
            Sirali gorev ID listesi veya None (dongu varsa).
        """
        in_degree: dict[str, int] = {tid: 0 for tid in nodes}
        for tid, node in nodes.items():
            for succ_id in node.successors:
                if succ_id in in_degree:
                    in_degree[succ_id] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            # Deterministik siralama icin sort
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            for succ_id in nodes[current].successors:
                if succ_id in in_degree:
                    in_degree[succ_id] -= 1
                    if in_degree[succ_id] == 0:
                        queue.append(succ_id)

        if len(result) != len(nodes):
            return None  # Dongu tespit edildi

        return result

    async def schedule(self) -> ScheduleResult:
        """Gorevleri zamanlar ve kritik yol analizi yapar.

        CPM (Critical Path Method) algoritmasi kullanir:
        1. Forward pass: en erken baslangic/bitis
        2. Backward pass: en gec baslangic/bitis
        3. Slack hesaplama
        4. Kritik yol belirleme

        Returns:
            ScheduleResult.
        """
        if not self.tasks:
            return ScheduleResult(feasible=True)

        # Dugum grafi olustur
        nodes: dict[str, _TaskNode] = {}
        for tid, info in self.tasks.items():
            nodes[tid] = _TaskNode(tid, info["name"], info["duration"])

        # Bagimliliklari ekle
        for tid, pred_ids in self.dependencies.items():
            if tid not in nodes:
                continue
            for pred_id in pred_ids:
                if pred_id not in nodes:
                    continue
                nodes[tid].predecessors.append(pred_id)
                nodes[pred_id].successors.append(tid)

        # Topolojik siralama
        order = self._topological_sort(nodes)
        if order is None:
            logger.error("Dongusel bagimlilik tespit edildi")
            return ScheduleResult(
                feasible=False,
                constraint_violations=["Dongusel bagimlilik tespit edildi"],
            )

        # Forward pass
        for tid in order:
            node = nodes[tid]
            if node.predecessors:
                node.earliest_start = max(
                    nodes[p].earliest_finish
                    for p in node.predecessors
                    if p in nodes
                )
            else:
                node.earliest_start = 0.0
            node.earliest_finish = node.earliest_start + node.duration

        # Proje suresi
        project_duration = max(
            n.earliest_finish for n in nodes.values()
        ) if nodes else 0.0

        # Backward pass
        for tid in reversed(order):
            node = nodes[tid]
            if node.successors:
                node.latest_finish = min(
                    nodes[s].latest_start
                    for s in node.successors
                    if s in nodes
                )
            else:
                node.latest_finish = project_duration
            node.latest_start = node.latest_finish - node.duration

        # Kisit kontrolu ve slack hesaplama
        violations: list[str] = []
        entries: list[ScheduleEntry] = []
        critical_path: list[str] = []

        for tid in order:
            node = nodes[tid]
            slack = node.latest_start - node.earliest_start
            on_critical = abs(slack) < 1e-9

            if on_critical:
                critical_path.append(tid)

            entries.append(ScheduleEntry(
                task_id=tid,
                task_name=node.task_name,
                start_time=node.earliest_start,
                end_time=node.earliest_finish,
                duration=node.duration,
                slack=max(0.0, slack),
                on_critical_path=on_critical,
            ))

        # Ek kisitlari kontrol et
        violations.extend(
            self._check_constraints(nodes, project_duration)
        )

        feasible = len(violations) == 0

        logger.info(
            "Zamanlama tamamlandi: %d gorev, sure=%.1f, kritik_yol=%d, feasible=%s",
            len(entries),
            project_duration,
            len(critical_path),
            feasible,
        )

        return ScheduleResult(
            entries=entries,
            total_duration=project_duration,
            critical_path=critical_path,
            feasible=feasible,
            constraint_violations=violations,
        )

    def _check_constraints(
        self, nodes: dict[str, _TaskNode], project_duration: float
    ) -> list[str]:
        """Ek zamansal kisitlari kontrol eder.

        Args:
            nodes: Zamanlanmis gorev dugumleri.
            project_duration: Toplam proje suresi.

        Returns:
            Ihlal mesajlari.
        """
        violations: list[str] = []

        for constraint in self.constraints:
            node = nodes.get(constraint.task_id)
            if node is None:
                continue

            if constraint.constraint_type == ConstraintType.DEADLINE:
                deadline = float(constraint.value) if constraint.value else 0.0
                if node.earliest_finish > deadline:
                    msg = (
                        f"Deadline ihlali: {node.task_name} "
                        f"(bitis={node.earliest_finish:.1f}, deadline={deadline:.1f})"
                    )
                    violations.append(msg)

            elif constraint.constraint_type == ConstraintType.START_AFTER:
                start_after = float(constraint.value) if constraint.value else 0.0
                if node.earliest_start < start_after:
                    msg = (
                        f"Start_after ihlali: {node.task_name} "
                        f"(baslangic={node.earliest_start:.1f}, minimum={start_after:.1f})"
                    )
                    violations.append(msg)

            elif constraint.constraint_type == ConstraintType.FINISH_BEFORE:
                finish_before = float(constraint.value) if constraint.value else 0.0
                if node.earliest_finish > finish_before:
                    msg = (
                        f"Finish_before ihlali: {node.task_name} "
                        f"(bitis={node.earliest_finish:.1f}, limit={finish_before:.1f})"
                    )
                    violations.append(msg)

            elif constraint.constraint_type == ConstraintType.DURATION_MAX:
                max_dur = float(constraint.value) if constraint.value else 0.0
                if node.duration > max_dur:
                    msg = (
                        f"Duration_max ihlali: {node.task_name} "
                        f"(sure={node.duration:.1f}, max={max_dur:.1f})"
                    )
                    violations.append(msg)

        return violations

    async def estimate_duration(
        self,
        task_id: str,
        optimistic: float,
        most_likely: float,
        pessimistic: float,
    ) -> float:
        """PERT formulu ile sure tahmini.

        Te = (O + 4M + P) / 6

        Args:
            task_id: Gorev ID.
            optimistic: Iyimser tahmin (saniye).
            most_likely: En olasi tahmin (saniye).
            pessimistic: Kotumser tahmin (saniye).

        Returns:
            Tahmini sure (saniye).
        """
        estimate = (optimistic + 4 * most_likely + pessimistic) / 6.0

        # Gorevi guncelle
        if task_id in self.tasks:
            self.tasks[task_id]["duration"] = estimate

        return estimate

    async def get_critical_path(self) -> list[str]:
        """Kritik yol gorev ID listesini dondurur.

        Returns:
            Kritik yol gorev ID listesi.
        """
        result = await self.schedule()
        return result.critical_path

    async def get_total_slack(self, task_id: str) -> float | None:
        """Belirtilen gorev icin toplam bollugu dondurur.

        Args:
            task_id: Gorev ID.

        Returns:
            Bolluk suresi (saniye) veya None.
        """
        result = await self.schedule()
        for entry in result.entries:
            if entry.task_id == task_id:
                return entry.slack
        return None
