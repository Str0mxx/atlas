"""ATLAS Event Sourcing Orkestratoru modulu.

Tam ES/CQRS pipeline, olay tekrarlama,
snapshot yonetimi, analitik
ve izleme.
"""

import logging
import time
from typing import Any

from app.core.eventsourcing.event_store import (
    EventStore,
)
from app.core.eventsourcing.event_publisher import (
    EventPublisher,
)
from app.core.eventsourcing.event_handler import (
    EventHandler,
)
from app.core.eventsourcing.aggregate_root import (
    AggregateRoot,
)
from app.core.eventsourcing.command_bus import (
    CommandBus,
)
from app.core.eventsourcing.query_handler import (
    QueryHandler,
)
from app.core.eventsourcing.projection_manager import (
    ProjectionManager,
)
from app.core.eventsourcing.saga_coordinator import (
    SagaCoordinator,
)

logger = logging.getLogger(__name__)


class EventSourcingOrchestrator:
    """Event Sourcing orkestratoru.

    Tum ES/CQRS bilesenlerini koordine eder.

    Attributes:
        store: Olay deposu.
        publisher: Olay yayincisi.
        handler: Olay isleyici.
        command_bus: Komut yolu.
        query_handler: Sorgu isleyici.
        projections: Projeksiyon yoneticisi.
        sagas: Saga koordinatoru.
    """

    def __init__(
        self,
        snapshot_frequency: int = 100,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            snapshot_frequency: Snapshot sikligi.
        """
        self._started_at = time.time()
        self._snapshot_frequency = snapshot_frequency

        self.store = EventStore()
        self.publisher = EventPublisher()
        self.handler = EventHandler()
        self.command_bus = CommandBus()
        self.query_handler = QueryHandler()
        self.projections = ProjectionManager()
        self.sagas = SagaCoordinator()

        self._aggregates: dict[
            str, AggregateRoot
        ] = {}

        logger.info(
            "EventSourcingOrchestrator baslatildi",
        )

    def emit_event(
        self,
        stream_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olay yayar.

        Args:
            stream_id: Akis ID.
            event_type: Olay tipi.
            data: Olay verisi.
            metadata: Ust veri.

        Returns:
            Olay bilgisi.
        """
        # Depoya kaydet
        event = self.store.append(
            stream_id, event_type,
            data, metadata,
        )

        # Isleyicilere gonder
        self.handler.handle(
            event_type,
            event_id=event["event_id"],
            data=data,
        )

        # Yayinla
        self.publisher.publish(
            event_type, data,
        )

        # Projeksiyonlara uygula
        self.projections.project_event(
            event_type, data,
        )

        # Otomatik snapshot
        version = self.store.get_stream_version(
            stream_id,
        )
        if (
            version > 0
            and version % self._snapshot_frequency
            == 0
        ):
            self.store.save_snapshot(
                stream_id,
                {"version": version},
                version,
            )

        return event

    def execute_command(
        self,
        command_type: str,
        payload: dict[str, Any] | None = None,
        actor: str = "",
    ) -> dict[str, Any]:
        """Komut yurutur.

        Args:
            command_type: Komut tipi.
            payload: Komut verisi.
            actor: Komutu veren.

        Returns:
            Yurutme sonucu.
        """
        return self.command_bus.dispatch(
            command_type, payload, actor,
        )

    def run_query(
        self,
        query_type: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sorgu calistirir.

        Args:
            query_type: Sorgu tipi.
            params: Parametreler.

        Returns:
            Sorgu sonucu.
        """
        return self.query_handler.query(
            query_type, params,
        )

    def create_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str = "default",
    ) -> AggregateRoot:
        """Aggregate olusturur.

        Args:
            aggregate_id: Aggregate ID.
            aggregate_type: Aggregate tipi.

        Returns:
            Aggregate nesnesi.
        """
        agg = AggregateRoot(
            aggregate_id, aggregate_type,
        )
        self._aggregates[aggregate_id] = agg
        return agg

    def get_aggregate(
        self,
        aggregate_id: str,
    ) -> AggregateRoot | None:
        """Aggregate getirir.

        Args:
            aggregate_id: Aggregate ID.

        Returns:
            Aggregate veya None.
        """
        return self._aggregates.get(
            aggregate_id,
        )

    def replay_events(
        self,
        stream_id: str,
        from_version: int = 0,
    ) -> dict[str, Any]:
        """Olaylari tekrarlar.

        Args:
            stream_id: Akis ID.
            from_version: Baslangic surumu.

        Returns:
            Tekrarlama sonucu.
        """
        events = self.store.read_stream(
            stream_id,
            from_version=from_version,
        )

        replayed = 0
        for event in events:
            self.handler.handle(
                event.get("event_type", ""),
                event_id=event.get(
                    "event_id", "",
                ),
                data=event.get("data"),
            )
            self.projections.project_event(
                event.get("event_type", ""),
                event.get("data"),
            )
            replayed += 1

        return {
            "stream_id": stream_id,
            "replayed": replayed,
            "from_version": from_version,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik bilgisi.
        """
        return {
            "total_events": self.store.event_count,
            "total_streams": self.store.stream_count,
            "total_commands": (
                self.command_bus.command_count
            ),
            "total_queries": (
                self.query_handler.query_count
            ),
            "active_sagas": (
                self.sagas.active_count
            ),
            "active_projections": (
                self.projections.active_count
            ),
            "subscribers": (
                self.publisher.subscriber_count
            ),
            "aggregates": len(self._aggregates),
            "snapshots": (
                self.store.snapshot_count
            ),
            "dead_letters": (
                self.publisher.dead_letter_count
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        """Sistem durumunu dondurur.

        Returns:
            Durum bilgisi.
        """
        return {
            "uptime": round(
                time.time() - self._started_at,
                2,
            ),
            "events": self.store.event_count,
            "streams": self.store.stream_count,
            "commands": (
                self.command_bus.command_count
            ),
            "queries": (
                self.query_handler.query_count
            ),
            "sagas": self.sagas.total_count,
            "projections": (
                self.projections.projection_count
            ),
            "aggregates": len(self._aggregates),
            "subscribers": (
                self.publisher.subscriber_count
            ),
        }
