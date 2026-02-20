import fnmatch
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"\bsudo\b",
    r"\beval\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bformat\b",
    r"\bchmod\s+777\b",
    r"\bdel\s+/[Ff]\b",
    r"\brd\s+/[Ss]\b",
]


class SandboxEnforcer:
    def __init__(self) -> None:
        self._allowed_paths: list[str] = []
        self._blocked_commands: list[str] = []
        self._resource_limits: dict[str, Any] = {}
        self._audit_log: list[dict] = []
        self._enabled: bool = True
        self._stats: dict[str, int] = {"checks": 0, "allowed": 0, "blocked": 0, "path_checks": 0, "audits": 0}
    @property
    def audit_count(self) -> int:
        return len(self._audit_log)
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        try:
            self._enabled = enabled
            return {"set": True, "enabled": enabled}
        except Exception as e:
            return {"set": False, "error": str(e)}
    def add_allowed_path(self, path: str = "") -> dict[str, Any]:
        try:
            if not path: return {"added": False, "error": "yol_gerekli"}
            if path not in self._allowed_paths: self._allowed_paths.append(path)
            return {"added": True, "path": path, "total": len(self._allowed_paths)}
        except Exception as e:
            return {"added": False, "error": str(e)}
    def remove_allowed_path(self, path: str = "") -> dict[str, Any]:
        try:
            if path not in self._allowed_paths: return {"removed": False, "error": "yol_bulunamadi"}
            self._allowed_paths.remove(path)
            return {"removed": True, "path": path}
        except Exception as e:
            return {"removed": False, "error": str(e)}
    def check_command(self, command: str = "") -> dict[str, Any]:
        try:
            if not command: return {"allowed": False, "error": "komut_gerekli"}
            self._stats["checks"] += 1
            if not self._enabled:
                self._stats["allowed"] += 1
                return {"allowed": True, "reason": "sandbox_devre_disi"}
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    self._stats["blocked"] += 1
                    self.audit("block_command", {"command": command, "pattern": pattern})
                    return {"allowed": False, "reason": "tehlikeli_komut", "pattern": pattern}
            for blocked in self._blocked_commands:
                pts = command.split()
                if pts and fnmatch.fnmatch(pts[0], blocked):
                    self._stats["blocked"] += 1
                    return {"allowed": False, "reason": "engellenen_komut", "blocked": blocked}
            self._stats["allowed"] += 1
            return {"allowed": True, "command": command}
        except Exception as e:
            return {"allowed": False, "error": str(e)}
    def check_path(self, path: str = "") -> dict[str, Any]:
        try:
            if not path: return {"allowed": False, "error": "yol_gerekli"}
            self._stats["path_checks"] += 1
            if not self._enabled: return {"allowed": True, "reason": "sandbox_devre_disi"}
            if not self._allowed_paths: return {"allowed": True, "reason": "kisitlama_yok"}
            abs_path = os.path.abspath(path)
            for allowed in self._allowed_paths:
                abs_allowed = os.path.abspath(allowed)
                if abs_path.startswith(abs_allowed): return {"allowed": True, "path": path, "matched": allowed}
            return {"allowed": False, "reason": "yol_izin_listesinde_degil", "path": path}
        except Exception as e:
            return {"allowed": False, "error": str(e)}
    def check_resources(self, limits: dict | None = None) -> dict[str, Any]:
        try:
            req = limits or {}
            violations = []
            for key, value in req.items():
                limit = self._resource_limits.get(key)
                if limit is not None and value > limit:
                    violations.append({"resource": key, "requested": value, "limit": limit})
            ok = len(violations) == 0
            return {"allowed": ok, "violations": violations, "checked": len(req)}
        except Exception as e:
            return {"allowed": False, "error": str(e)}
    def set_resource_limit(self, resource: str = "", limit: Any = None) -> dict[str, Any]:
        try:
            if not resource: return {"set": False, "error": "kaynak_gerekli"}
            self._resource_limits[resource] = limit
            return {"set": True, "resource": resource, "limit": limit}
        except Exception as e:
            return {"set": False, "error": str(e)}
    def block_dangerous(self, command: str = "") -> dict[str, Any]:
        try:
            if not command: return {"dangerous": False, "error": "komut_gerekli"}
            matches = [pat for pat in DANGEROUS_PATTERNS if re.search(pat, command, re.IGNORECASE)]
            if matches:
                self.audit("dangerous_detected", {"command": command, "patterns": matches})
                return {"dangerous": True, "patterns": matches, "count": len(matches)}
            return {"dangerous": False, "command": command}
        except Exception as e:
            return {"dangerous": False, "error": str(e)}
    def add_blocked_command(self, pattern: str = "") -> dict[str, Any]:
        try:
            if not pattern: return {"added": False, "error": "desen_gerekli"}
            if pattern not in self._blocked_commands: self._blocked_commands.append(pattern)
            return {"added": True, "pattern": pattern}
        except Exception as e:
            return {"added": False, "error": str(e)}
    def audit(self, action: str = "", details: dict | None = None) -> dict[str, Any]:
        try:
            if not action: return {"recorded": False, "error": "aksiyon_gerekli"}
            record = {"action": action, "details": details or {}, "timestamp": time.time()}
            self._audit_log.append(record)
            self._stats["audits"] += 1
            return {"recorded": True, "action": action}
        except Exception as e:
            return {"recorded": False, "error": str(e)}
    def get_audit_log(self, limit: int = 20) -> dict[str, Any]:
        try:
            recent = self._audit_log[-limit:] if limit > 0 else list(self._audit_log)
            return {"retrieved": True, "log": recent, "total": len(self._audit_log), "returned": len(recent)}
        except Exception as e:
            return {"retrieved": False, "error": str(e)}
    def get_summary(self) -> dict[str, Any]:
        try:
            return {"retrieved": True, "enabled": self._enabled, "allowed_paths": len(self._allowed_paths), "blocked_commands": len(self._blocked_commands), "resource_limits": len(self._resource_limits), "audit_count": self.audit_count, "stats": dict(self._stats)}
        except Exception as e:
            return {"retrieved": False, "error": str(e)}
