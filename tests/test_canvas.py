"""Live Canvas & A2UI Engine test modulu.

Canvas sunucu, A2UI ayristirici, bilesen render,
WebSocket yonetimi ve oturum yonetimi testleri.
"""

import pytest
import time

from app.models.canvas_models import (
    A2UIComponent,
    CanvasCommand,
    CanvasConfig,
    CanvasPushRequest,
    CanvasSession,
    CanvasSnapshot,
    ComponentType,
    WebSocketClient,
)
from app.core.canvas.canvas_session import CanvasSessionManager
from app.core.canvas.component_renderer import ComponentRenderer
from app.core.canvas.a2ui_parser import A2UIParser
from app.core.canvas.websocket_manager import WebSocketManager
from app.core.canvas.canvas_server import CanvasServer


class TestCanvasModels:
    """Canvas model testleri."""

    def test_component_type_values(self) -> None:
        """ComponentType enum degerlerini dogrular."""
        assert ComponentType.TEXT == "text"
        assert ComponentType.BUTTON == "button"
        assert ComponentType.ROW == "row"
        assert ComponentType.COLUMN == "column"
        assert ComponentType.CARD == "card"
        assert ComponentType.CONTAINER == "container"
        assert ComponentType.INPUT == "input"
        assert ComponentType.IMAGE == "image"

    def test_canvas_command_values(self) -> None:
        """CanvasCommand enum degerlerini dogrular."""
        assert CanvasCommand.SURFACE_UPDATE == "surfaceUpdate"
        assert CanvasCommand.RESET == "reset"
        assert CanvasCommand.EVAL == "eval"
        assert CanvasCommand.SNAPSHOT == "snapshot"
        assert CanvasCommand.BEGIN_RENDERING == "beginRendering"

    def test_a2ui_component_defaults(self) -> None:
        """A2UIComponent varsayilan degerlerini dogrular."""
        comp = A2UIComponent()
        assert comp.type == ComponentType.TEXT
        assert comp.id == ""
        assert comp.props == {}
        assert comp.children == []
        assert comp.text == ""

    def test_a2ui_component_with_children(self) -> None:
        """Ic ice bilesen yapisi olusturur."""
        child = A2UIComponent(type=ComponentType.TEXT, text="hello")
        parent = A2UIComponent(type=ComponentType.CARD, id="card-1", children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].text == "hello"

    def test_canvas_session_defaults(self) -> None:
        """CanvasSession varsayilan degerlerini dogrular."""
        session = CanvasSession()
        assert session.session_id == ""
        assert session.is_active is True
        assert session.components == []

    def test_canvas_push_request(self) -> None:
        """CanvasPushRequest olusturmayi dogrular."""
        req = CanvasPushRequest(session_id="s1", command=CanvasCommand.SURFACE_UPDATE, html="<p>test</p>")
        assert req.session_id == "s1"
        assert req.command == CanvasCommand.SURFACE_UPDATE

    def test_canvas_snapshot_defaults(self) -> None:
        """CanvasSnapshot varsayilan degerlerini dogrular."""
        snap = CanvasSnapshot()
        assert snap.width == 1920
        assert snap.height == 1080
        assert snap.format == "png"

    def test_websocket_client_defaults(self) -> None:
        """WebSocketClient varsayilan degerlerini dogrular."""
        client = WebSocketClient()
        assert client.is_alive is True
        assert client.capabilities == []

    def test_canvas_config_defaults(self) -> None:
        """CanvasConfig varsayilan degerlerini dogrular."""
        config = CanvasConfig()
        assert config.port == 18793
        assert config.max_sessions == 100
        assert config.enable_js_eval is False
        assert config.max_component_depth == 10


class TestCanvasSession:
    """Canvas oturum yonetimi testleri."""

    def test_create_session(self) -> None:
        mgr = CanvasSessionManager()
        session = mgr.create_session()
        assert session.session_id != ""
        assert session.is_active is True

    def test_get_session(self) -> None:
        mgr = CanvasSessionManager()
        session = mgr.create_session()
        result = mgr.get_session(session.session_id)
        assert result is not None
        assert result.session_id == session.session_id

    def test_get_nonexistent_session(self) -> None:
        mgr = CanvasSessionManager()
        assert mgr.get_session("nonexistent") is None

    def test_close_session(self) -> None:
        mgr = CanvasSessionManager()
        session = mgr.create_session()
        assert mgr.close_session(session.session_id) is True
        assert mgr.get_session(session.session_id) is None

    def test_close_nonexistent_session(self) -> None:
        mgr = CanvasSessionManager()
        assert mgr.close_session("nonexistent") is False

    def test_max_sessions_limit(self) -> None:
        config = CanvasConfig(max_sessions=2)
        mgr = CanvasSessionManager(config=config)
        mgr.create_session()
        mgr.create_session()
        with pytest.raises(RuntimeError):
            mgr.create_session()

    def test_validate_path_traversal(self) -> None:
        mgr = CanvasSessionManager()
        session = mgr.create_session()
        assert mgr.validate_path(session.session_id, "../../etc/passwd") is False

    def test_validate_path_valid(self) -> None:
        mgr = CanvasSessionManager()
        session = mgr.create_session()
        valid_path = session.root_dir + "/file.png"
        assert mgr.validate_path(session.session_id, valid_path) is True

    def test_validate_path_nonexistent_session(self) -> None:
        mgr = CanvasSessionManager()
        assert mgr.validate_path("nonexistent", "/some/path") is False

    def test_list_sessions(self) -> None:
        mgr = CanvasSessionManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        mgr.close_session(s1.session_id)
        sessions = mgr.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == s2.session_id

    def test_cleanup_expired(self) -> None:
        config = CanvasConfig(session_timeout=0)
        mgr = CanvasSessionManager(config=config)
        mgr.create_session()
        mgr.create_session()
        count = mgr.cleanup_expired()
        assert count == 2

    def test_get_history(self) -> None:
        mgr = CanvasSessionManager()
        mgr.create_session()
        history = mgr.get_history()
        assert len(history) >= 1
        assert history[0]["action"] == "create_session"

    def test_get_stats(self) -> None:
        mgr = CanvasSessionManager()
        mgr.create_session()
        stats = mgr.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["active_sessions"] == 1


class TestComponentRenderer:
    """Bilesen render testleri."""

    def test_render_text(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.TEXT, text="hello", id="t1")
        html = renderer.render(comp)
        assert "hello" in html
        assert "t1" in html

    def test_render_button(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.BUTTON, text="Click", id="b1")
        html = renderer.render(comp)
        assert "<button" in html
        assert "Click" in html

    def test_render_input(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.INPUT, id="i1", props={"placeholder": "Enter text"})
        html = renderer.render(comp)
        assert "<input" in html
        assert "Enter text" in html

    def test_render_image(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.IMAGE, id="img1", props={"src": "test.png", "alt": "Test"})
        html = renderer.render(comp)
        assert "<img" in html
        assert "test.png" in html

    def test_render_card_with_children(self) -> None:
        renderer = ComponentRenderer()
        child = A2UIComponent(type=ComponentType.TEXT, text="inside")
        comp = A2UIComponent(type=ComponentType.CARD, id="c1", children=[child])
        html = renderer.render(comp)
        assert "inside" in html
        assert "card" in html

    def test_render_row(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.ROW, id="r1")
        html = renderer.render(comp)
        assert "flex-direction:row" in html

    def test_render_column(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.COLUMN, id="col1")
        html = renderer.render(comp)
        assert "flex-direction:column" in html

    def test_sanitize_html_xss(self) -> None:
        renderer = ComponentRenderer()
        result = renderer.sanitize_html("<script>alert(1)</script>")
        assert "<script" not in result

    def test_sanitize_html_empty(self) -> None:
        renderer = ComponentRenderer()
        assert renderer.sanitize_html("") == ""

    def test_apply_styles(self) -> None:
        renderer = ComponentRenderer()
        result = renderer.apply_styles("<p>test</p>", {"color": "red"})
        assert "color:red" in result

    def test_render_container(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.CONTAINER, id="cont1")
        html = renderer.render(comp)
        assert "container" in html

    def test_get_stats(self) -> None:
        renderer = ComponentRenderer()
        comp = A2UIComponent(type=ComponentType.TEXT, text="test")
        renderer.render(comp)
        stats = renderer.get_stats()
        assert stats["total_renders"] == 1


class TestA2UIParser:
    """A2UI ayristirici testleri."""

    def test_parse_command_valid_json(self) -> None:
        parser = A2UIParser()
        result = parser.parse_command("{\"type\": \"text\", \"text\": \"hello\"}")
        assert result is not None
        assert result["text"] == "hello"

    def test_parse_command_invalid_json(self) -> None:
        parser = A2UIParser()
        result = parser.parse_command("not json")
        assert result is None

    def test_parse_jsonl_empty(self) -> None:
        parser = A2UIParser()
        results = parser.parse_jsonl("")
        assert len(results) == 0

    def test_validate_component_valid(self) -> None:
        parser = A2UIParser()
        comp = A2UIComponent(type=ComponentType.TEXT, text="test")
        assert parser.validate_component(comp) is True

    def test_validate_component_max_depth(self) -> None:
        parser = A2UIParser(max_depth=2)
        deep = A2UIComponent(type=ComponentType.TEXT, text="deep")
        mid = A2UIComponent(type=ComponentType.CARD, children=[deep])
        top = A2UIComponent(type=ComponentType.CARD, children=[mid])
        outer = A2UIComponent(type=ComponentType.CARD, children=[top])
        assert parser.validate_component(outer) is False

    def test_build_tree(self) -> None:
        parser = A2UIParser()
        data = [{"type": "text", "text": "hello", "id": "t1"}, {"type": "button", "text": "click", "id": "b1"}]
        tree = parser.build_tree(data)
        assert len(tree) == 2
        assert tree[0].text == "hello"

    def test_build_tree_with_children(self) -> None:
        parser = A2UIParser()
        data = [{"type": "card", "id": "c1", "children": [{"type": "text", "text": "child"}]}]
        tree = parser.build_tree(data)
        assert len(tree) == 1
        assert len(tree[0].children) == 1

    def test_to_html(self) -> None:
        parser = A2UIParser()
        comp = A2UIComponent(type=ComponentType.TEXT, text="test")
        html = parser.to_html(comp)
        assert "test" in html

    def test_get_stats(self) -> None:
        parser = A2UIParser()
        parser.parse_command("{\"type\": \"text\"}")
        stats = parser.get_stats()
        assert stats["total_parsed"] == 1
        assert stats["total_errors"] == 0

    def test_get_history(self) -> None:
        parser = A2UIParser()
        parser.parse_jsonl("{\"x\":1}")
        assert len(parser.get_history()) >= 1

class TestWebSocketManager:
    """WebSocket yonetimi testleri."""

    def test_connect(self) -> None:
        mgr = WebSocketManager()
        client = mgr.connect("c1", "s1")
        assert client.client_id == "c1"
        assert client.is_alive is True

    def test_disconnect(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        assert mgr.disconnect("c1") is True

    def test_disconnect_nonexistent(self) -> None:
        mgr = WebSocketManager()
        assert mgr.disconnect("nonexistent") is False

    def test_broadcast(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        mgr.connect("c2", "s1")
        sent = mgr.broadcast("s1", {"data": "test"})
        assert sent == 2

    def test_send(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        assert mgr.send("c1", {"data": "test"}) is True

    def test_get_clients(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        mgr.connect("c2", "s1")
        clients = mgr.get_clients("s1")
        assert len(clients) == 2

    def test_ping_all(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        results = mgr.ping_all()
        assert all(results.values())

    def test_get_stats(self) -> None:
        mgr = WebSocketManager()
        mgr.connect("c1", "s1")
        stats = mgr.get_stats()
        assert stats["total_clients"] == 1

class TestCanvasServer:
    """Canvas sunucu testleri."""

    def test_create_session(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        assert session.is_active is True

    def test_push_html(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        result = server.push(session.session_id, html="<p>test</p>")
        assert result is True

    def test_push_invalid_session(self) -> None:
        server = CanvasServer()
        result = server.push("invalid", html="test")
        assert result is False

    def test_reset(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        assert server.reset(session.session_id) is True

    def test_eval_js_disabled(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        result = server.eval_js(session.session_id, "console.log(1)")
        assert result is False

    def test_eval_js_enabled(self) -> None:
        config = CanvasConfig(enable_js_eval=True)
        server = CanvasServer(config=config)
        session = server.create_session()
        result = server.eval_js(session.session_id, "console.log(1)")
        assert result is True

    def test_eval_js_dangerous(self) -> None:
        config = CanvasConfig(enable_js_eval=True)
        server = CanvasServer(config=config)
        session = server.create_session()
        result = server.eval_js(session.session_id, "eval(dangerous)")
        assert result is False

    def test_snapshot(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        snap = server.snapshot(session.session_id)
        assert snap is not None

    def test_close_session(self) -> None:
        server = CanvasServer()
        session = server.create_session()
        assert server.close_session(session.session_id) is True

    def test_list_sessions(self) -> None:
        server = CanvasServer()
        server.create_session()
        server.create_session()
        assert len(server.list_sessions()) == 2

    def test_get_stats(self) -> None:
        server = CanvasServer()
        server.create_session()
        stats = server.get_stats()
        assert "session_stats" in stats

    def test_get_history(self) -> None:
        server = CanvasServer()
        server.create_session()
        assert len(server.get_history()) >= 1