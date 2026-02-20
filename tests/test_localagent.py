"""Tests for app.core.localagent package - 163 tests."""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.localagent.agent_bridge import AgentBridge
from app.core.localagent.shell_executor import ShellExecutor
from app.core.localagent.filesystem_navigator import FileSystemNavigator
from app.core.localagent.process_manager import ProcessManager
from app.core.localagent.clipboard_access import ClipboardAccess
from app.core.localagent.screen_capture import AgentScreenCapture
from app.core.localagent.sandbox_enforcer import SandboxEnforcer
from app.core.localagent.command_whitelist import CommandWhitelist


class TestAgentBridge:
    def test_init(self):
        ab = AgentBridge()
        assert ab.is_connected is False
        assert ab.reconnect_count == 0

    def test_establish(self):
        ab = AgentBridge()
        r = ab.establish("127.0.0.1", 9000)
        assert r["established"] is True
        assert r["host"] == "127.0.0.1"
        assert r["port"] == 9000

    def test_establish_sets_connected(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        assert ab.is_connected is True

    def test_authenticate(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.authenticate("secret_token")
        assert r["authenticated"] is True

    def test_authenticate_no_connection(self):
        ab = AgentBridge()
        r = ab.authenticate("token")
        assert r["authenticated"] is False

    def test_authenticate_empty_token(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.authenticate("")
        assert r["authenticated"] is False

    def test_send_heartbeat_connected(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.send_heartbeat()
        assert r["sent"] is True

    def test_send_heartbeat_disconnected(self):
        ab = AgentBridge()
        r = ab.send_heartbeat()
        assert r["sent"] is False

    def test_check_heartbeat_fresh(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        ab.send_heartbeat()
        r = ab.check_heartbeat()
        assert r["healthy"] is True

    def test_check_heartbeat_no_heartbeat(self):
        ab = AgentBridge()
        r = ab.check_heartbeat()
        assert r["healthy"] is False

    def test_disconnect(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.disconnect()
        assert r["disconnected"] is True
        assert ab.is_connected is False

    def test_disconnect_not_connected(self):
        ab = AgentBridge()
        r = ab.disconnect()
        assert r["disconnected"] is True  # idempotent - always returns True

    def test_reconnect_after_disconnect(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        ab.disconnect()
        r = ab.reconnect()
        assert r["reconnected"] is True

    def test_reconnect_no_prior_host(self):
        ab = AgentBridge()
        r = ab.reconnect()
        assert r["reconnected"] is False

    def test_send_message_connected(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.send_message({"type": "cmd", "payload": "ls"})
        assert r["sent"] is True

    def test_send_message_disconnected(self):
        ab = AgentBridge()
        r = ab.send_message({"type": "cmd"})
        assert r["sent"] is False

    def test_send_message_empty(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.send_message({})
        assert r["sent"] is False

    def test_get_status_connected(self):
        ab = AgentBridge()
        ab.establish("127.0.0.1", 9000)
        r = ab.get_status()
        assert r["retrieved"] is True
        assert r["connected"] is True

    def test_get_status_disconnected(self):
        ab = AgentBridge()
        r = ab.get_status()
        assert r["retrieved"] is True
        assert r["connected"] is False

    def test_get_summary(self):
        ab = AgentBridge()
        r = ab.get_summary()
        assert r["retrieved"] is True
        assert "reconnect_attempts" in r or "stats" in r


class TestShellExecutor:
    def test_init(self):
        se = ShellExecutor()
        assert se.history_count == 0

    def test_execute_simple_command(self):
        se = ShellExecutor()
        r = se.execute("echo hello")
        assert r["executed"] is True
        assert r["returncode"] == 0

    def test_execute_empty(self):
        se = ShellExecutor()
        r = se.execute("")
        assert r["executed"] is False

    def test_execute_simple_method(self):
        se = ShellExecutor()
        r = se.execute_simple("echo test")
        assert r["executed"] is True

    def test_execute_simple_empty(self):
        se = ShellExecutor()
        r = se.execute_simple("")
        assert r["executed"] is False

    def test_history_tracked(self):
        se = ShellExecutor()
        se.execute("echo a")
        se.execute("echo b")
        assert se.history_count == 2

    def test_get_history(self):
        se = ShellExecutor()
        se.execute("echo hello")
        r = se.get_history()
        assert r["retrieved"] is True
        assert r["total"] >= 1

    def test_get_history_limit(self):
        se = ShellExecutor()
        for i in range(5):
            se.execute(f"echo {i}")
        r = se.get_history(limit=3)
        assert r["returned"] == 3

    def test_set_working_directory_valid(self, tmp_path):
        se = ShellExecutor()
        r = se.set_working_directory(str(tmp_path))
        assert r["set"] is True

    def test_set_working_directory_invalid(self):
        se = ShellExecutor()
        r = se.set_working_directory("/nonexistent_dir_xyz_abc")
        assert r["set"] is False

    def test_set_working_directory_empty(self):
        se = ShellExecutor()
        r = se.set_working_directory("")
        assert r["set"] is False

    def test_set_env_var(self):
        se = ShellExecutor()
        r = se.set_env_var("TEST_VAR", "test_value")
        assert r["set"] is True

    def test_set_env_var_empty_key(self):
        se = ShellExecutor()
        r = se.set_env_var("", "value")
        assert r["set"] is False

    def test_get_environment(self):
        se = ShellExecutor()
        se.set_env_var("MY_VAR", "42")
        r = se.get_environment()
        assert r["retrieved"] is True
        assert "MY_VAR" in r["env"]

    def test_cancel(self):
        se = ShellExecutor()
        r = se.cancel()
        assert "cancelled" in r

    def test_get_summary(self):
        se = ShellExecutor()
        r = se.get_summary()
        assert r["retrieved"] is True
        assert "history_count" in r


class TestFileSystemNavigator:
    def test_init(self):
        fn = FileSystemNavigator()
        assert fn.history_count == 0

    def test_list_directory_valid(self, tmp_path):
        fn = FileSystemNavigator()
        r = fn.list_directory(str(tmp_path))
        assert r["listed"] is True
        assert "entries" in r

    def test_list_directory_invalid(self):
        fn = FileSystemNavigator()
        r = fn.list_directory("/nonexistent_xyz_dir_abc_123")
        assert r["listed"] is False

    def test_read_file(self, tmp_path):
        fn = FileSystemNavigator()
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        r = fn.read_file(str(f))
        assert r["read"] is True
        assert "hello world" in r["content"]

    def test_read_file_missing(self):
        fn = FileSystemNavigator()
        r = fn.read_file("/nonexistent_xyz_abc_123.txt")
        assert r["read"] is False

    def test_read_file_empty_path(self):
        fn = FileSystemNavigator()
        r = fn.read_file("")
        assert r["read"] is False

    def test_write_file(self, tmp_path):
        fn = FileSystemNavigator()
        f = tmp_path / "out.txt"
        r = fn.write_file(str(f), "content here")
        assert r["written"] is True
        assert f.read_text() == "content here"

    def test_write_file_empty_path(self):
        fn = FileSystemNavigator()
        r = fn.write_file("", "data")
        assert r["written"] is False

    def test_delete_file(self, tmp_path):
        fn = FileSystemNavigator()
        f = tmp_path / "del.txt"
        f.write_text("bye")
        r = fn.delete(str(f))
        assert r["deleted"] is True
        assert not f.exists()

    def test_delete_missing(self):
        fn = FileSystemNavigator()
        r = fn.delete("/nonexistent_xyz_abc_123.txt")
        assert r["deleted"] is False

    def test_delete_empty_path(self):
        fn = FileSystemNavigator()
        r = fn.delete("")
        assert r["deleted"] is False

    def test_create_directory(self, tmp_path):
        fn = FileSystemNavigator()
        d = tmp_path / "newdir"
        r = fn.create_directory(str(d))
        assert r["created"] is True
        assert d.is_dir()

    def test_create_directory_empty(self):
        fn = FileSystemNavigator()
        r = fn.create_directory("")
        assert r["created"] is False

    def test_search(self, tmp_path):
        fn = FileSystemNavigator()
        (tmp_path / "a.txt").write_text("alpha")
        (tmp_path / "b.txt").write_text("beta")
        r = fn.search("*.txt", str(tmp_path))
        assert r["searched"] is True
        assert r["count"] >= 2

    def test_search_empty_pattern(self):
        fn = FileSystemNavigator()
        r = fn.search("")
        assert r["searched"] is False

    def test_get_permissions(self, tmp_path):
        fn = FileSystemNavigator()
        f = tmp_path / "perm.txt"
        f.write_text("x")
        r = fn.get_permissions(str(f))
        assert r["retrieved"] is True

    def test_get_permissions_missing(self):
        fn = FileSystemNavigator()
        r = fn.get_permissions("/nonexistent_xyz_abc_123.txt")
        assert r["retrieved"] is False

    def test_resolve_path(self, tmp_path):
        fn = FileSystemNavigator()
        r = fn.resolve_path(str(tmp_path))
        assert r["resolved"] is True

    def test_copy(self, tmp_path):
        fn = FileSystemNavigator()
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("copy me")
        r = fn.copy(str(src), str(dst))
        assert r["copied"] is True
        assert dst.read_text() == "copy me"

    def test_copy_missing_src(self, tmp_path):
        fn = FileSystemNavigator()
        r = fn.copy("/nonexistent_xyz_abc_123.txt", str(tmp_path / "dst.txt"))
        assert r["copied"] is False

    def test_get_summary(self):
        fn = FileSystemNavigator()
        r = fn.get_summary()
        assert r["retrieved"] is True
        assert "history_count" in r


class TestProcessManager:
    def test_init(self):
        pm = ProcessManager()
        assert pm.managed_count == 0

    def test_list_processes(self):
        pm = ProcessManager()
        r = pm.list_processes()
        assert r["listed"] is True
        assert isinstance(r["processes"], list)

    def test_get_process_missing(self):
        pm = ProcessManager()
        r = pm.get_process(999999999)
        assert r["retrieved"] is False

    def test_start_process(self):
        import sys as _sys
        pm = ProcessManager()
        r = pm.start_process(_sys.executable, ["-c", "import time; time.sleep(0.3)"])
        assert r["started"] is True
        assert "pid" in r
        pm.kill_process(r["pid"])

    def test_start_process_empty_cmd(self):
        pm = ProcessManager()
        r = pm.start_process("")
        assert r["started"] is False

    def test_stop_process_missing(self):
        pm = ProcessManager()
        r = pm.stop_process(999999999)
        assert r["stopped"] is False

    def test_kill_process_missing(self):
        pm = ProcessManager()
        r = pm.kill_process(999999999)
        assert r["killed"] is False

    def test_get_resource_usage_current(self):
        import os as _os
        pm = ProcessManager()
        r = pm.get_resource_usage(_os.getpid())
        assert r["retrieved"] is True

    def test_get_resource_usage_missing(self):
        pm = ProcessManager()
        r = pm.get_resource_usage(999999999)
        assert r["retrieved"] is False

    def test_monitor(self):
        import os as _os
        pm = ProcessManager()
        r = pm.monitor(_os.getpid())
        assert r["monitoring"] is True
        assert pm.monitored_count == 1

    def test_unmonitor(self):
        import os as _os
        pm = ProcessManager()
        pid = _os.getpid()
        pm.monitor(pid)
        r = pm.unmonitor(pid)
        assert r["unmonitored"] is True

    def test_unmonitor_not_monitored(self):
        pm = ProcessManager()
        r = pm.unmonitor(999999999)
        assert r["unmonitored"] is False

    def test_get_summary(self):
        pm = ProcessManager()
        r = pm.get_summary()
        assert r["retrieved"] is True
        assert "managed_count" in r


class TestClipboardAccess:
    def test_init(self):
        ca = ClipboardAccess()
        assert ca.history_count == 0

    def test_write_and_read(self):
        ca = ClipboardAccess()
        ca.write("hello clipboard")
        r = ca.read()
        assert r["read"] is True
        assert r["content"] == "hello clipboard"

    def test_read_empty_clipboard(self):
        ca = ClipboardAccess()
        r = ca.read()
        assert r["read"] is True

    def test_clear(self):
        ca = ClipboardAccess()
        ca.write("something")
        r = ca.clear()
        assert r["cleared"] is True

    def test_history_grows(self):
        ca = ClipboardAccess()
        ca.write("a")
        ca.write("b")
        ca.write("c")
        assert ca.history_count == 2  # first write sets current, subsequent writes add to history

    def test_get_history(self):
        ca = ClipboardAccess()
        ca.write("x")
        ca.write("y")
        r = ca.get_history()
        assert r["retrieved"] is True
        assert r["total"] == 1  # first write sets current, second write adds first to history

    def test_get_history_limit(self):
        ca = ClipboardAccess()
        for i in range(5):
            ca.write(f"item{i}")
        r = ca.get_history(limit=3)
        assert r["returned"] == 3

    def test_get_format_text(self):
        ca = ClipboardAccess()
        ca.write("plain text")
        r = ca.get_format()
        assert r["retrieved"] is True
        assert r["format"] == "text"

    def test_get_summary(self):
        ca = ClipboardAccess()
        r = ca.get_summary()
        assert r["retrieved"] is True
        assert "history_count" in r

class TestAgentScreenCapture:
    def test_init(self):
        sc = AgentScreenCapture()
        assert sc.capture_count == 0
        assert sc.is_recording is False

    def test_capture_screen_valid(self):
        sc = AgentScreenCapture()
        r = sc.capture_screen(fmt="png")
        assert r["captured"] is True
        assert r["format"] == "png"

    def test_capture_screen_invalid_format(self):
        sc = AgentScreenCapture()
        r = sc.capture_screen(fmt="xyz")
        assert r["captured"] is False

    def test_capture_screen_increments_count(self):
        sc = AgentScreenCapture()
        sc.capture_screen(fmt="png")
        assert sc.capture_count == 1

    def test_capture_region_valid(self):
        sc = AgentScreenCapture()
        r = sc.capture_region(x=0, y=0, width=400, height=300, fmt="png")
        assert r["captured"] is True
        assert r["region"]["width"] == 400

    def test_capture_region_invalid_dims(self):
        sc = AgentScreenCapture()
        r = sc.capture_region(width=0, height=0)
        assert r["captured"] is False

    def test_capture_region_invalid_format(self):
        sc = AgentScreenCapture()
        r = sc.capture_region(width=100, height=100, fmt="tiff")
        assert r["captured"] is False

    def test_capture_window_by_id(self):
        sc = AgentScreenCapture()
        r = sc.capture_window(window_id="12345")
        assert r["captured"] is True

    def test_capture_window_by_title(self):
        sc = AgentScreenCapture()
        r = sc.capture_window(window_title="My Window")
        assert r["captured"] is True

    def test_capture_window_no_params(self):
        sc = AgentScreenCapture()
        r = sc.capture_window()
        assert r["captured"] is False

    def test_start_recording(self):
        sc = AgentScreenCapture()
        r = sc.start_recording(fps=15, fmt="mp4")
        assert r["started"] is True
        assert sc.is_recording is True
        sc.stop_recording()

    def test_start_recording_already_recording(self):
        sc = AgentScreenCapture()
        sc.start_recording()
        r = sc.start_recording()
        assert r["started"] is False
        sc.stop_recording()

    def test_stop_recording(self):
        sc = AgentScreenCapture()
        sc.start_recording()
        r = sc.stop_recording()
        assert r["stopped"] is True
        assert sc.is_recording is False

    def test_stop_recording_not_active(self):
        sc = AgentScreenCapture()
        r = sc.stop_recording()
        assert r["stopped"] is False

    def test_compress(self):
        sc = AgentScreenCapture()
        cap_r = sc.capture_screen(fmt="png")
        cid = cap_r["capture_id"]
        r = sc.compress(cid, quality=50)
        assert r["compressed"] is True
        assert r["quality"] == 50

    def test_compress_invalid_id(self):
        sc = AgentScreenCapture()
        r = sc.compress("nonexistent_id")
        assert r["compressed"] is False

    def test_compress_empty_id(self):
        sc = AgentScreenCapture()
        r = sc.compress("")
        assert r["compressed"] is False

    def test_get_captures(self):
        sc = AgentScreenCapture()
        sc.capture_screen()
        sc.capture_screen()
        r = sc.get_captures(limit=10)
        assert r["retrieved"] is True
        assert r["total"] == 2

    def test_get_summary(self):
        sc = AgentScreenCapture()
        r = sc.get_summary()
        assert r["retrieved"] is True
        assert "capture_count" in r
        assert "is_recording" in r

class TestSandboxEnforcer:
    def test_init(self):
        se = SandboxEnforcer()
        assert se.is_enabled is True
        assert se.audit_count == 0

    def test_set_enabled_false(self):
        se = SandboxEnforcer()
        r = se.set_enabled(False)
        assert r["set"] is True
        assert se.is_enabled is False

    def test_check_command_safe(self):
        assert SandboxEnforcer().check_command("ls -la")["allowed"] is True

    def test_check_command_empty(self):
        assert SandboxEnforcer().check_command("")["allowed"] is False

    def test_check_command_shutdown(self):
        assert SandboxEnforcer().check_command("shutdown /s")["allowed"] is False

    def test_check_command_sudo(self):
        assert SandboxEnforcer().check_command("sudo apt")["allowed"] is False

    def test_check_command_eval(self):
        assert SandboxEnforcer().check_command("eval bad")["allowed"] is False

    def test_check_command_reboot(self):
        assert SandboxEnforcer().check_command("reboot")["allowed"] is False

    def test_check_command_rm_rf(self):
        assert SandboxEnforcer().check_command("rm -rf /")["allowed"] is False

    def test_check_command_chmod(self):
        assert SandboxEnforcer().check_command("chmod 777 /etc/passwd")["allowed"] is False

    def test_check_command_del(self):
        assert SandboxEnforcer().check_command("del /F file.txt")["allowed"] is False

    def test_check_command_rd(self):
        assert SandboxEnforcer().check_command("rd /S /Q mydir")["allowed"] is False

    def test_check_command_sandbox_disabled(self):
        se = SandboxEnforcer(); se.set_enabled(False)
        assert se.check_command("rm -rf /")["allowed"] is True

    def test_check_command_custom_blocked(self):
        se = SandboxEnforcer(); se.add_blocked_command("badapp")
        assert se.check_command("badapp --run")["allowed"] is False

    def test_add_allowed_path(self):
        r = SandboxEnforcer().add_allowed_path("/tmp/safe")
        assert r["added"] is True and r["total"] == 1

    def test_add_allowed_path_empty(self):
        assert SandboxEnforcer().add_allowed_path("")["added"] is False

    def test_remove_allowed_path(self):
        se = SandboxEnforcer(); se.add_allowed_path("/tmp/safe")
        assert se.remove_allowed_path("/tmp/safe")["removed"] is True

    def test_remove_allowed_path_missing(self):
        assert SandboxEnforcer().remove_allowed_path("/tmp/none")["removed"] is False

    def test_check_path_allowed(self, tmp_path):
        se = SandboxEnforcer(); se.add_allowed_path(str(tmp_path))
        assert se.check_path(str(tmp_path / "f.txt"))["allowed"] is True

    def test_check_path_denied(self, tmp_path):
        se = SandboxEnforcer(); se.add_allowed_path(str(tmp_path / "safe"))
        assert se.check_path("/etc/passwd")["allowed"] is False

    def test_check_path_empty(self):
        assert SandboxEnforcer().check_path("")["allowed"] is False

    def test_check_path_no_restrictions(self):
        assert SandboxEnforcer().check_path("/anywhere")["allowed"] is True

    def test_check_resources_ok(self):
        se = SandboxEnforcer(); se.set_resource_limit("memory_mb", 512)
        assert se.check_resources({"memory_mb": 256})["allowed"] is True

    def test_check_resources_exceeded(self):
        se = SandboxEnforcer(); se.set_resource_limit("memory_mb", 512)
        r = se.check_resources({"memory_mb": 1024})
        assert r["allowed"] is False and len(r["violations"]) == 1

    def test_check_resources_empty(self):
        assert SandboxEnforcer().check_resources({})["allowed"] is True

    def test_set_resource_limit(self):
        assert SandboxEnforcer().set_resource_limit("cpu", 80)["set"] is True

    def test_set_resource_limit_empty(self):
        assert SandboxEnforcer().set_resource_limit("", 80)["set"] is False

    def test_block_dangerous_detected(self):
        assert SandboxEnforcer().block_dangerous("sudo shutdown")["dangerous"] is True

    def test_block_dangerous_clean(self):
        assert SandboxEnforcer().block_dangerous("ls -la")["dangerous"] is False

    def test_block_dangerous_empty(self):
        assert SandboxEnforcer().block_dangerous("")["dangerous"] is False

    def test_add_blocked_command(self):
        assert SandboxEnforcer().add_blocked_command("badapp")["added"] is True

    def test_add_blocked_command_empty(self):
        assert SandboxEnforcer().add_blocked_command("")["added"] is False

    def test_audit(self):
        se = SandboxEnforcer()
        r = se.audit("test_event", {"key": "value"})
        assert r["recorded"] is True and se.audit_count == 1

    def test_audit_empty_action(self):
        assert SandboxEnforcer().audit("")["recorded"] is False

    def test_get_audit_log(self):
        se = SandboxEnforcer(); se.audit("a1"); se.audit("a2")
        r = se.get_audit_log()
        assert r["retrieved"] is True and r["total"] >= 2

    def test_get_audit_log_limit(self):
        se = SandboxEnforcer()
        [se.audit(f"a{i}") for i in range(5)]
        assert se.get_audit_log(limit=3)["returned"] == 3

    def test_get_summary(self):
        r = SandboxEnforcer().get_summary()
        assert r["retrieved"] is True and r["enabled"] is True

class TestCommandWhitelist:
    def test_init(self):
        cw = CommandWhitelist()
        assert cw.entry_count > 0
        assert cw.override_count == 0

    def test_default_commands_allowed(self):
        cw = CommandWhitelist()
        for cmd in ["ls", "dir", "pwd", "echo", "cat", "git", "python"]:
            assert cw.check(cmd)["allowed"] is True

    def test_unknown_command_denied(self):
        assert CommandWhitelist().check("unknownapp_xyz_12345")["allowed"] is False

    def test_check_empty(self):
        assert CommandWhitelist().check("")["allowed"] is False

    def test_add_pattern(self):
        r = CommandWhitelist().add("myapp", risk_level=3, description="custom")
        assert r["added"] is True and r["pattern"] == "myapp"

    def test_add_empty_pattern(self):
        assert CommandWhitelist().add("")["added"] is False

    def test_add_then_check(self):
        cw = CommandWhitelist(); cw.add("myapp")
        assert cw.check("myapp --flag")["allowed"] is True

    def test_add_risk_clamped_max(self):
        assert CommandWhitelist().add("app1", risk_level=20)["risk"] == 10

    def test_add_risk_clamped_min(self):
        assert CommandWhitelist().add("app2", risk_level=-5)["risk"] == 1

    def test_remove_pattern(self):
        cw = CommandWhitelist(); cw.add("tempapp")
        assert cw.remove("tempapp")["removed"] is True

    def test_remove_nonexistent(self):
        assert CommandWhitelist().remove("nonexistent_xyz")["removed"] is False

    def test_remove_empty(self):
        assert CommandWhitelist().remove("")["removed"] is False

    def test_score_risk_safe(self):
        r = CommandWhitelist().score_risk("ls -la")
        assert r["scored"] is True and r["level"] in ["low", "medium", "high", "critical"]

    def test_score_risk_pipe(self):
        r = CommandWhitelist().score_risk("ls | grep foo")
        assert r["scored"] is True and r["bonus"] >= 1

    def test_score_risk_redirect(self):
        r = CommandWhitelist().score_risk("echo hi > file.txt")
        assert r["scored"] is True and r["bonus"] >= 1

    def test_score_risk_chain(self):
        r = CommandWhitelist().score_risk("echo a && echo b")
        assert r["scored"] is True and r["bonus"] >= 1

    def test_score_risk_empty(self):
        assert CommandWhitelist().score_risk("")["scored"] is False

    def test_add_override_block(self):
        cw = CommandWhitelist(); cw.add_override("ls", allowed=False, reason="test")
        assert cw.check("ls -la")["allowed"] is False

    def test_add_override_empty(self):
        assert CommandWhitelist().add_override("")["added"] is False

    def test_remove_override(self):
        cw = CommandWhitelist(); cw.add_override("ls", allowed=False)
        assert cw.remove_override("ls")["removed"] is True
        assert cw.override_count == 0

    def test_remove_override_nonexistent(self):
        assert CommandWhitelist().remove_override("nonexistent")["removed"] is False

    def test_get_all(self):
        cw = CommandWhitelist()
        r = cw.get_all()
        assert r["retrieved"] is True and r["count"] == cw.entry_count

    def test_get_log(self):
        cw = CommandWhitelist(); cw.add("testapp")
        r = cw.get_log()
        assert r["retrieved"] is True and r["total"] >= 1

    def test_get_log_limit(self):
        cw = CommandWhitelist()
        [cw.add(f"app{i}") for i in range(5)]
        assert cw.get_log(limit=3)["returned"] == 3

    def test_get_summary(self):
        r = CommandWhitelist().get_summary()
        assert r["retrieved"] is True and "entry_count" in r and "stats" in r

    def test_stats_tracked(self):
        cw = CommandWhitelist()
        cw.check("ls"); cw.check("ls"); cw.check("unknownapp")
        s = cw.get_summary()
        assert s["stats"]["checks"] == 3
        assert s["stats"]["allowed"] == 2 and s["stats"]["denied"] == 1

    def test_glob_pattern_matching(self):
        cw = CommandWhitelist(); cw.add("myapp*")
        assert cw.check("myapp")["allowed"] is True
        assert cw.check("myapp_runner")["allowed"] is True
