"""Unified Dashboard & Control Panel testleri."""

import pytest

from app.models.dashboard_models import (
    WidgetType,
    DashboardTheme,
    ExportFormat,
    StreamStatus,
    LayoutMode,
    PlatformType,
    DashboardRecord,
    WidgetRecord,
    ViewRecord,
    ExportRecord,
)
from app.core.dashboard.dashboard_engine import (
    DashboardEngine,
)
from app.core.dashboard.widget_manager import (
    WidgetManager,
)
from app.core.dashboard.realtime_data_stream import (
    RealtimeDataStream,
)
from app.core.dashboard.custom_view_builder import (
    CustomViewBuilder,
)
from app.core.dashboard.mobile_dashboard import (
    MobileDashboard,
)
from app.core.dashboard.telegram_dashboard import (
    TelegramDashboard,
)
from app.core.dashboard.drag_drop_layout_editor import (
    DragDropLayoutEditor,
)
from app.core.dashboard.dashboard_export_manager import (
    DashboardExportManager,
)
from app.core.dashboard.dashboard_orchestrator import (
    DashboardOrchestrator,
)


# ── Model Testleri ──


class TestDashboardModels:
    """Model testleri."""

    def test_widget_type_values(self):
        assert WidgetType.chart == "chart"
        assert WidgetType.table == "table"
        assert WidgetType.metric == "metric"
        assert WidgetType.gauge == "gauge"
        assert WidgetType.timeline == "timeline"
        assert WidgetType.map_widget == "map_widget"

    def test_dashboard_theme_values(self):
        assert DashboardTheme.light == "light"
        assert DashboardTheme.dark == "dark"
        assert DashboardTheme.system == "system"
        assert DashboardTheme.custom == "custom"
        assert DashboardTheme.high_contrast == "high_contrast"

    def test_export_format_values(self):
        assert ExportFormat.pdf == "pdf"
        assert ExportFormat.png == "png"
        assert ExportFormat.csv == "csv"
        assert ExportFormat.json == "json"
        assert ExportFormat.excel == "excel"
        assert ExportFormat.html == "html"

    def test_stream_status_values(self):
        assert StreamStatus.connected == "connected"
        assert StreamStatus.disconnected == "disconnected"
        assert StreamStatus.reconnecting == "reconnecting"
        assert StreamStatus.paused == "paused"
        assert StreamStatus.error == "error"

    def test_layout_mode_values(self):
        assert LayoutMode.grid == "grid"
        assert LayoutMode.freeform == "freeform"
        assert LayoutMode.stacked == "stacked"
        assert LayoutMode.responsive == "responsive"
        assert LayoutMode.compact == "compact"

    def test_platform_type_values(self):
        assert PlatformType.web == "web"
        assert PlatformType.mobile == "mobile"
        assert PlatformType.telegram == "telegram"
        assert PlatformType.desktop == "desktop"
        assert PlatformType.tablet == "tablet"
        assert PlatformType.api == "api"

    def test_dashboard_record(self):
        r = DashboardRecord(
            name="Main", theme="dark"
        )
        assert r.name == "Main"
        assert r.theme == "dark"
        assert r.dashboard_id

    def test_widget_record(self):
        r = WidgetRecord(
            name="CPU", widget_type="gauge"
        )
        assert r.name == "CPU"
        assert r.widget_type == "gauge"
        assert r.widget_id

    def test_view_record(self):
        r = ViewRecord(name="My View")
        assert r.name == "My View"
        assert r.view_id

    def test_export_record(self):
        r = ExportRecord(
            format="pdf", status="completed"
        )
        assert r.format == "pdf"
        assert r.export_id


# ── DashboardEngine Testleri ──


class TestDashboardEngine:
    """Dashboard motoru testleri."""

    def setup_method(self):
        self.de = DashboardEngine()

    def test_init(self):
        assert self.de.dashboard_count == 0

    def test_create_dashboard(self):
        r = self.de.create_dashboard(
            name="Main Dashboard",
            theme="dark",
            layout="grid",
        )
        assert r["created"] is True
        assert r["name"] == "Main Dashboard"
        assert r["theme"] == "dark"
        assert self.de.dashboard_count == 1

    def test_manage_layout(self):
        d = self.de.create_dashboard(
            name="Test",
        )
        r = self.de.manage_layout(
            dashboard_id=d["dashboard_id"],
            layout="responsive",
            columns=4,
            gap_px=12,
        )
        assert r["managed"] is True
        assert r["columns"] == 4

    def test_manage_layout_not_found(self):
        r = self.de.manage_layout(
            dashboard_id="nonexistent",
        )
        assert r["managed"] is False

    def test_apply_theme(self):
        d = self.de.create_dashboard(
            name="Test",
        )
        r = self.de.apply_theme(
            dashboard_id=d["dashboard_id"],
            theme="light",
            primary_color="#ff5722",
        )
        assert r["applied"] is True
        assert r["theme"] == "light"

    def test_apply_theme_not_found(self):
        r = self.de.apply_theme(
            dashboard_id="nonexistent",
        )
        assert r["applied"] is False

    def test_configure_responsive(self):
        d = self.de.create_dashboard(
            name="Test",
        )
        r = self.de.configure_responsive(
            dashboard_id=d["dashboard_id"],
        )
        assert r["configured"] is True
        assert r["breakpoint_count"] == 4

    def test_optimize_performance(self):
        d = self.de.create_dashboard(
            name="Test",
        )
        r = self.de.optimize_performance(
            dashboard_id=d["dashboard_id"],
        )
        assert r["optimized"] is True
        assert r["performance"] == "excellent"
        assert r["caching"] is True

    def test_optimize_not_found(self):
        r = self.de.optimize_performance(
            dashboard_id="nonexistent",
        )
        assert r["optimized"] is False


# ── WidgetManager Testleri ──


class TestWidgetManager:
    """Widget yöneticisi testleri."""

    def setup_method(self):
        self.wm = WidgetManager()

    def test_init(self):
        assert self.wm.widget_count == 0

    def test_get_library(self):
        r = self.wm.get_library()
        assert r["retrieved"] is True
        assert r["widget_types"] == 5
        assert r["total_variants"] > 10

    def test_create_widget(self):
        r = self.wm.create_widget(
            name="CPU Gauge",
            widget_type="gauge",
            variant="circular",
            data_source="system_metrics",
        )
        assert r["created"] is True
        assert r["type"] == "gauge"
        assert self.wm.widget_count == 1

    def test_configure_widget(self):
        w = self.wm.create_widget(
            name="Test",
        )
        r = self.wm.configure_widget(
            widget_id=w["widget_id"],
            config={"color": "blue", "size": "lg"},
        )
        assert r["configured"] is True
        assert "color" in r["config_keys"]

    def test_configure_not_found(self):
        r = self.wm.configure_widget(
            widget_id="nonexistent",
        )
        assert r["configured"] is False

    def test_bind_data(self):
        w = self.wm.create_widget(
            name="Test",
        )
        r = self.wm.bind_data(
            widget_id=w["widget_id"],
            data_source="postgres",
            query="SELECT * FROM metrics",
        )
        assert r["bound"] is True
        assert r["data_source"] == "postgres"

    def test_bind_data_not_found(self):
        r = self.wm.bind_data(
            widget_id="nonexistent",
        )
        assert r["bound"] is False

    def test_set_refresh_realtime(self):
        w = self.wm.create_widget(
            name="Test",
        )
        r = self.wm.set_refresh(
            widget_id=w["widget_id"],
            refresh_sec=3,
        )
        assert r["set"] is True
        assert r["frequency"] == "realtime"

    def test_set_refresh_slow(self):
        w = self.wm.create_widget(
            name="Test",
        )
        r = self.wm.set_refresh(
            widget_id=w["widget_id"],
            refresh_sec=300,
        )
        assert r["frequency"] == "slow"


# ── RealtimeDataStream Testleri ──


class TestRealtimeDataStream:
    """Gerçek zamanlı veri akışı testleri."""

    def setup_method(self):
        self.rds = RealtimeDataStream()

    def test_init(self):
        assert self.rds.stream_count == 0

    def test_create_stream(self):
        r = self.rds.create_stream(
            name="metrics",
            data_source="system",
            interval_ms=1000,
        )
        assert r["created"] is True
        assert r["interval_ms"] == 1000
        assert self.rds.stream_count == 1

    def test_manage_connection_connect(self):
        s = self.rds.create_stream(
            name="test",
        )
        r = self.rds.manage_connection(
            stream_id=s["stream_id"],
            action="connect",
        )
        assert r["managed"] is True
        assert r["subscribers"] == 1

    def test_manage_connection_disconnect(self):
        s = self.rds.create_stream(
            name="test",
        )
        c = self.rds.manage_connection(
            stream_id=s["stream_id"],
            action="connect",
            client_id="client_1",
        )
        r = self.rds.manage_connection(
            stream_id=s["stream_id"],
            action="disconnect",
            client_id="client_1",
        )
        assert r["managed"] is True
        assert r["subscribers"] == 0

    def test_manage_connection_not_found(self):
        r = self.rds.manage_connection(
            stream_id="nonexistent",
        )
        assert r["managed"] is False

    def test_batch_updates(self):
        updates = [
            {"metric": f"m{i}", "value": i}
            for i in range(25)
        ]
        r = self.rds.batch_updates(
            updates=updates, batch_size=10,
        )
        assert r["batched"] is True
        assert r["batch_count"] == 3
        assert r["total_updates"] == 25

    def test_batch_updates_empty(self):
        r = self.rds.batch_updates()
        assert r["batched"] is True
        assert r["batch_count"] == 0

    def test_stream_data(self):
        s = self.rds.create_stream(
            name="test",
        )
        self.rds.manage_connection(
            stream_id=s["stream_id"],
            action="connect",
        )
        r = self.rds.stream_data(
            stream_id=s["stream_id"],
            data_points=[{"v": 1}, {"v": 2}],
        )
        assert r["streamed"] is True
        assert r["data_points"] == 2
        assert r["total_delivered"] == 2

    def test_configure_fallback(self):
        s = self.rds.create_stream(
            name="test",
        )
        r = self.rds.configure_fallback(
            stream_id=s["stream_id"],
            fallback_method="polling",
            poll_interval_ms=5000,
        )
        assert r["configured"] is True
        assert r["fallback_method"] == "polling"


# ── CustomViewBuilder Testleri ──


class TestCustomViewBuilder:
    """Özel görünüm oluşturucu testleri."""

    def setup_method(self):
        self.cvb = CustomViewBuilder()

    def test_init(self):
        assert self.cvb.view_count == 0

    def test_create_view(self):
        r = self.cvb.create_view(
            name="Task View",
            base_data="tasks",
        )
        assert r["created"] is True
        assert r["name"] == "Task View"
        assert self.cvb.view_count == 1

    def test_configure_filters(self):
        v = self.cvb.create_view(name="Test")
        r = self.cvb.configure_filters(
            view_id=v["view_id"],
            filters=[
                {"field": "status", "value": "active"},
                {"field": "priority", "value": "high"},
            ],
        )
        assert r["configured"] is True
        assert r["filter_count"] == 2

    def test_configure_filters_not_found(self):
        r = self.cvb.configure_filters(
            view_id="nonexistent",
        )
        assert r["configured"] is False

    def test_select_columns(self):
        v = self.cvb.create_view(name="Test")
        r = self.cvb.select_columns(
            view_id=v["view_id"],
            columns=["name", "status", "date"],
        )
        assert r["selected"] is True
        assert r["column_count"] == 3

    def test_set_sort(self):
        v = self.cvb.create_view(name="Test")
        r = self.cvb.set_sort(
            view_id=v["view_id"],
            sort_by="date",
            direction="desc",
        )
        assert r["set"] is True
        assert r["direction"] == "desc"

    def test_save_and_share(self):
        v = self.cvb.create_view(name="Test")
        r = self.cvb.save_and_share(
            view_id=v["view_id"],
            share=True,
        )
        assert r["saved"] is True
        assert r["shared"] is True
        assert r["share_url"] is not None

    def test_save_without_share(self):
        v = self.cvb.create_view(name="Test")
        r = self.cvb.save_and_share(
            view_id=v["view_id"],
            share=False,
        )
        assert r["saved"] is True
        assert r["share_url"] is None


# ── MobileDashboard Testleri ──


class TestMobileDashboard:
    """Mobil gösterge paneli testleri."""

    def setup_method(self):
        self.md = MobileDashboard()

    def test_init(self):
        assert self.md.config_count == 0

    def test_optimize_mobile(self):
        r = self.md.optimize_mobile(
            dashboard_id="db_test",
            target_platform="ios",
        )
        assert r["optimized"] is True
        assert r["optimization_count"] == 5
        assert self.md.config_count == 1

    def test_configure_gestures(self):
        r = self.md.configure_gestures()
        assert r["configured"] is True
        assert r["gesture_count"] == 5

    def test_configure_gestures_custom(self):
        r = self.md.configure_gestures(
            gestures=["swipe_refresh", "pinch_zoom"],
        )
        assert r["gesture_count"] == 2

    def test_enable_offline(self):
        r = self.md.enable_offline(
            dashboard_id="db_test",
            cache_size_mb=50,
        )
        assert r["enabled"] is True
        assert r["cache_level"] == "standard"
        assert r["service_worker"] is True

    def test_enable_offline_aggressive(self):
        r = self.md.enable_offline(
            cache_size_mb=200,
        )
        assert r["cache_level"] == "aggressive"

    def test_setup_push_notifications(self):
        r = self.md.setup_push_notifications(
            channels=["alerts", "updates", "reports"],
        )
        assert r["configured"] is True
        assert r["channel_count"] == 3
        assert r["push_enabled"] is True

    def test_add_quick_action(self):
        r = self.md.add_quick_action(
            name="View Tasks",
            action_type="navigate",
            target="/tasks",
        )
        assert r["added"] is True
        assert r["total_actions"] == 1


# ── TelegramDashboard Testleri ──


class TestTelegramDashboard:
    """Telegram gösterge paneli testleri."""

    def setup_method(self):
        self.td = TelegramDashboard()

    def test_init(self):
        assert self.td.command_count == 0

    def test_generate_mini_dashboard(self):
        r = self.td.generate_mini_dashboard()
        assert r["generated"] is True
        assert r["metric_count"] == 3
        assert "ATLAS" in r["message"]

    def test_generate_mini_custom(self):
        r = self.td.generate_mini_dashboard(
            metrics=[
                {"name": "Sales", "value": "$1.2K"},
            ],
        )
        assert r["metric_count"] == 1

    def test_register_command(self):
        r = self.td.register_command(
            command="/stats",
            description="Show stats",
            handler="handle_stats",
        )
        assert r["registered"] is True
        assert r["total_commands"] == 1

    def test_send_inline_update(self):
        r = self.td.send_inline_update(
            chat_id="12345",
            metric_name="CPU",
            old_value="45%",
            new_value="72%",
        )
        assert r["sent"] is True
        assert "45%" in r["message"]
        assert "72%" in r["message"]

    def test_get_quick_stats(self):
        r = self.td.get_quick_stats()
        assert r["retrieved"] is True
        assert r["category_count"] == 3

    def test_get_quick_stats_custom(self):
        r = self.td.get_quick_stats(
            categories=["system"],
        )
        assert r["category_count"] == 1

    def test_integrate_alerts(self):
        r = self.td.integrate_alerts(
            severity_filter="high",
        )
        assert r["integrated"] is True
        assert r["type_count"] == 4


# ── DragDropLayoutEditor Testleri ──


class TestDragDropLayoutEditor:
    """Sürükle bırak düzenleyici testleri."""

    def setup_method(self):
        self.ddle = DragDropLayoutEditor()

    def test_init(self):
        assert self.ddle.item_count == 0

    def test_place_widget(self):
        r = self.ddle.place_widget(
            widget_id="wg_test",
            row=0, col=0,
            width=3, height=2,
        )
        assert r["placed"] is True
        assert self.ddle.item_count == 1

    def test_configure_grid(self):
        r = self.ddle.configure_grid(
            columns=12,
            row_height=80,
            gap_px=8,
            snap=True,
        )
        assert r["configured"] is True
        assert r["total_cells"] == 240

    def test_snap_to_grid(self):
        self.ddle.place_widget(
            widget_id="wg_test",
            row=3, col=7,
        )
        r = self.ddle.snap_to_grid(
            widget_id="wg_test",
            grid_size=4,
        )
        assert r["snapped"] is True
        assert r["new_pos"]["row"] == 4
        assert r["new_pos"]["col"] == 8

    def test_snap_not_found(self):
        r = self.ddle.snap_to_grid(
            widget_id="nonexistent",
        )
        assert r["snapped"] is False

    def test_resize_widget(self):
        self.ddle.place_widget(
            widget_id="wg_test",
            width=2, height=1,
        )
        r = self.ddle.resize_widget(
            widget_id="wg_test",
            new_width=4,
            new_height=3,
        )
        assert r["resized"] is True
        assert r["new_size"]["width"] == 4

    def test_resize_not_found(self):
        r = self.ddle.resize_widget(
            widget_id="nonexistent",
        )
        assert r["resized"] is False

    def test_undo(self):
        self.ddle.place_widget(
            widget_id="wg_1",
        )
        assert self.ddle.item_count == 1
        r = self.ddle.undo()
        assert r["undone"] is True
        assert self.ddle.item_count == 0

    def test_undo_nothing(self):
        r = self.ddle.undo()
        assert r["undone"] is False

    def test_redo(self):
        self.ddle.place_widget(
            widget_id="wg_1",
        )
        self.ddle.undo()
        assert self.ddle.item_count == 0
        r = self.ddle.redo()
        assert r["redone"] is True
        assert self.ddle.item_count == 1

    def test_redo_nothing(self):
        r = self.ddle.redo()
        assert r["redone"] is False


# ── DashboardExportManager Testleri ──


class TestDashboardExportManager:
    """Dışa aktarma yöneticisi testleri."""

    def setup_method(self):
        self.dem = DashboardExportManager()

    def test_init(self):
        assert self.dem.export_count == 0

    def test_export_pdf(self):
        r = self.dem.export_pdf(
            dashboard_id="db_test",
            page_size="A4",
            orientation="landscape",
        )
        assert r["exported"] is True
        assert r["format"] == "pdf"
        assert r["filename"].endswith(".pdf")

    def test_export_image(self):
        r = self.dem.export_image(
            dashboard_id="db_test",
            image_format="png",
            width=1920,
        )
        assert r["exported"] is True
        assert r["format"] == "png"
        assert r["resolution"] == "1920x1080"

    def test_export_data(self):
        r = self.dem.export_data(
            dashboard_id="db_test",
            data_format="csv",
        )
        assert r["exported"] is True
        assert r["format"] == "csv"
        assert r["include_headers"] is True

    def test_schedule_report(self):
        r = self.dem.schedule_report(
            dashboard_id="db_test",
            frequency="weekly",
            export_format="pdf",
        )
        assert r["scheduled"] is True
        assert r["interval_days"] == 7

    def test_schedule_report_monthly(self):
        r = self.dem.schedule_report(
            frequency="monthly",
        )
        assert r["interval_days"] == 30

    def test_distribute_email(self):
        e = self.dem.export_pdf(
            dashboard_id="db_test",
        )
        r = self.dem.distribute_email(
            export_id=e["export_id"],
            recipients=[
                "user1@test.com",
                "user2@test.com",
            ],
            subject="Weekly Report",
        )
        assert r["distributed"] is True
        assert r["recipient_count"] == 2

    def test_distribute_not_found(self):
        r = self.dem.distribute_email(
            export_id="nonexistent",
        )
        assert r["distributed"] is False


# ── DashboardOrchestrator Testleri ──


class TestDashboardOrchestrator:
    """Gösterge paneli orkestratör testleri."""

    def setup_method(self):
        self.orch = DashboardOrchestrator()

    def test_init(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["components"] == 8

    def test_full_dashboard_setup(self):
        r = self.orch.full_dashboard_setup(
            name="ATLAS Main",
            theme="dark",
        )
        assert r["completed"] is True
        assert r["widgets_created"] == 3

    def test_full_dashboard_custom_widgets(self):
        r = self.orch.full_dashboard_setup(
            widgets=[
                {"name": "Sales", "type": "chart"},
                {"name": "Revenue", "type": "metric"},
            ],
        )
        assert r["completed"] is True
        assert r["widgets_created"] == 2

    def test_multi_platform_deploy(self):
        self.orch.full_dashboard_setup()
        r = self.orch.multi_platform_deploy(
            dashboard_id="db_test",
        )
        assert r["deployed"] is True
        assert "web" in r["platforms"]
        assert r["platform_count"] >= 2

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["dashboards"] == 0
        assert r["widgets"] == 0

    def test_get_analytics_after_setup(self):
        self.orch.full_dashboard_setup()
        r = self.orch.get_analytics()
        assert r["dashboards"] == 1
        assert r["widgets"] == 3
        assert r["streams"] == 1
