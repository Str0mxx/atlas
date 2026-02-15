"""ATLAS Akis Orkestratoru modulu.

Tam akis pipeline yonetimi,
topoloji, kontrol noktasi,
kurtarma ve izleme.
"""

import logging
import time
from typing import Any

from app.core.streaming.aggregator import (
    StreamAggregator,
)
from app.core.streaming.cep_engine import (
    CEPEngine,
)
from app.core.streaming.realtime_dashboard import (
    RealtimeDashboard,
)
from app.core.streaming.stream_joiner import (
    StreamJoiner,
)
from app.core.streaming.stream_processor import (
    StreamProcessor,
)
from app.core.streaming.stream_sink import (
    StreamSink,
)
from app.core.streaming.stream_source import (
    StreamSource,
)
from app.core.streaming.window_manager import (
    WindowManager,
)

logger = logging.getLogger(__name__)


class StreamingOrchestrator:
    """Akis orkestratoru.

    Tum akis bilesenlierini koordine eder.

    Attributes:
        source: Akis kaynagi.
        processor: Akis isleyici.
        windows: Pencere yoneticisi.
        aggregator: Toplayici.
        joiner: Birlestirici.
        cep: CEP motoru.
        sink: Akis cikisi.
        dashboard: Gercek zamanli panel.
    """

    def __init__(
        self,
        window_size: int = 60,
        max_lateness: int = 10,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            window_size: Pencere boyutu.
            max_lateness: Maks gecikme.
        """
        self.source = StreamSource()
        self.processor = StreamProcessor()
        self.windows = WindowManager(
            window_size, max_lateness,
        )
        self.aggregator = StreamAggregator()
        self.joiner = StreamJoiner()
        self.cep = CEPEngine()
        self.sink = StreamSink()
        self.dashboard = RealtimeDashboard()

        self._topologies: dict[
            str, dict[str, Any]
        ] = {}
        self._checkpoints: list[
            dict[str, Any]
        ] = []
        self._initialized = False

        logger.info(
            "StreamingOrchestrator baslatildi",
        )

    def initialize(
        self,
        config: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Sistemi baslatir.

        Args:
            config: Konfigurasyon.

        Returns:
            Baslangic bilgisi.
        """
        self._initialized = True
        return {
            "status": "initialized",
            "components": 8,
            "config": config or {},
        }

    def create_topology(
        self,
        name: str,
        source: str,
        chain: str,
        sink: str,
        window: str | None = None,
    ) -> dict[str, Any]:
        """Topoloji olusturur.

        Args:
            name: Topoloji adi.
            source: Kaynak adi.
            chain: Islem zinciri.
            sink: Cikis adi.
            window: Pencere adi.

        Returns:
            Topoloji bilgisi.
        """
        self._topologies[name] = {
            "name": name,
            "source": source,
            "chain": chain,
            "sink": sink,
            "window": window,
            "status": "active",
            "events_processed": 0,
            "created_at": time.time(),
        }

        return {
            "name": name,
            "status": "active",
        }

    def process_event(
        self,
        topology: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Topoloji uzerinden olay isler.

        Args:
            topology: Topoloji adi.
            event: Olay verisi.

        Returns:
            Isleme sonucu.
        """
        topo = self._topologies.get(topology)
        if not topo:
            return {"error": "topology_not_found"}

        # Kaynak
        self.source.emit(topo["source"], event)

        # Isleme
        result = self.processor.process(
            topo["chain"], event,
        )

        if result is None:
            return {"status": "filtered"}

        # Pencere
        if topo["window"]:
            self.windows.add_event(
                topo["window"], result,
            )

        # CEP
        cep_result = self.cep.process_event(result)

        # Cikis
        self.sink.write(topo["sink"], result)

        topo["events_processed"] += 1

        return {
            "status": "processed",
            "cep_matches": cep_result.get(
                "matches", [],
            ),
            "topology": topology,
        }

    def process_batch(
        self,
        topology: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu olay isler.

        Args:
            topology: Topoloji adi.
            events: Olaylar.

        Returns:
            Isleme sonucu.
        """
        processed = 0
        filtered = 0
        alerts = 0

        for event in events:
            r = self.process_event(
                topology, event,
            )
            if r.get("status") == "processed":
                processed += 1
                alerts += len(
                    r.get("cep_matches", []),
                )
            elif r.get("status") == "filtered":
                filtered += 1

        return {
            "topology": topology,
            "total": len(events),
            "processed": processed,
            "filtered": filtered,
            "alerts": alerts,
        }

    def checkpoint(self) -> dict[str, Any]:
        """Kontrol noktasi olusturur.

        Returns:
            Checkpoint bilgisi.
        """
        cp = {
            "topologies": len(self._topologies),
            "sources": self.source.source_count,
            "sinks": self.sink.sink_count,
            "windows": self.windows.window_count,
            "processor_state": dict(
                self.processor._state,
            ),
            "timestamp": time.time(),
        }
        self._checkpoints.append(cp)

        return {
            "checkpoint_id": len(
                self._checkpoints,
            ),
            "status": "saved",
        }

    def recover(
        self,
        checkpoint_id: int | None = None,
    ) -> dict[str, Any]:
        """Kontrol noktasindan kurtarir.

        Args:
            checkpoint_id: Checkpoint ID.

        Returns:
            Kurtarma bilgisi.
        """
        if not self._checkpoints:
            return {"error": "no_checkpoints"}

        idx = (
            checkpoint_id - 1
            if checkpoint_id
            else len(self._checkpoints) - 1
        )
        if idx < 0 or idx >= len(self._checkpoints):
            return {"error": "invalid_checkpoint"}

        cp = self._checkpoints[idx]
        # Durumu geri yukle
        for k, v in cp.get(
            "processor_state", {},
        ).items():
            self.processor.set_state(k, v)

        return {
            "checkpoint_id": idx + 1,
            "status": "recovered",
        }

    def get_topology(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Topoloji bilgisini getirir.

        Args:
            name: Topoloji adi.

        Returns:
            Topoloji bilgisi veya None.
        """
        return self._topologies.get(name)

    def stop_topology(
        self,
        name: str,
    ) -> bool:
        """Topolojiyi durdurur.

        Args:
            name: Topoloji adi.

        Returns:
            Basarili mi.
        """
        topo = self._topologies.get(name)
        if topo:
            topo["status"] = "stopped"
            return True
        return False

    def get_snapshot(self) -> dict[str, Any]:
        """Snapshot getirir.

        Returns:
            Snapshot bilgisi.
        """
        return {
            "sources": self.source.source_count,
            "active_sources": (
                self.source.active_count
            ),
            "chains": self.processor.chain_count,
            "processed": (
                self.processor.processed_count
            ),
            "windows": self.windows.window_count,
            "aggregations": (
                self.aggregator.aggregation_count
            ),
            "streams_joined": (
                self.joiner.stream_count
            ),
            "cep_patterns": (
                self.cep.pattern_count
            ),
            "cep_alerts": self.cep.alert_count,
            "sinks": self.sink.sink_count,
            "dashboards": (
                self.dashboard.dashboard_count
            ),
            "topologies": len(self._topologies),
            "checkpoints": len(self._checkpoints),
            "initialized": self._initialized,
            "timestamp": time.time(),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu getirir.

        Returns:
            Analitik bilgisi.
        """
        return {
            "sources": {
                "total": (
                    self.source.source_count
                ),
                "active": (
                    self.source.active_count
                ),
                "total_received": (
                    self.source.total_received
                ),
            },
            "processing": {
                "chains": (
                    self.processor.chain_count
                ),
                "processed": (
                    self.processor.processed_count
                ),
                "errors": (
                    self.processor.error_count
                ),
            },
            "windows": {
                "active": (
                    self.windows.window_count
                ),
                "closed": (
                    self.windows.closed_count
                ),
            },
            "cep": {
                "patterns": (
                    self.cep.pattern_count
                ),
                "sequences": (
                    self.cep.sequence_count
                ),
                "alerts": self.cep.alert_count,
            },
            "sinks": {
                "total": self.sink.sink_count,
                "active": self.sink.active_count,
                "written": (
                    self.sink.total_written
                ),
            },
            "dashboards": {
                "total": (
                    self.dashboard.dashboard_count
                ),
                "widgets": (
                    self.dashboard.widget_count
                ),
                "metrics": (
                    self.dashboard.metric_count
                ),
            },
            "timestamp": time.time(),
        }

    @property
    def topology_count(self) -> int:
        """Topoloji sayisi."""
        return len(self._topologies)

    @property
    def checkpoint_count(self) -> int:
        """Checkpoint sayisi."""
        return len(self._checkpoints)

    @property
    def is_initialized(self) -> bool:
        """Baslatildi mi."""
        return self._initialized
