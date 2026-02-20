import fnmatch
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SAFE_COMMANDS = ['ls', 'dir', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'which', 'where', 'whoami', 'date', 'python', 'python3', 'pip', 'git', 'curl', 'wget']

RISK_LEVELS = {'low': 1, 'medium': 5, 'high': 8, 'critical': 10}


class CommandWhitelist:
    def __init__(self) -> None:
        self._entries: dict[str, dict] = {}
        self._overrides: list[dict] = []
        self._log: list[dict] = []
        self._stats: dict[str, int] = {'added': 0, 'removed': 0, 'checks': 0, 'allowed': 0, 'denied': 0}
        for cmd in DEFAULT_SAFE_COMMANDS:
            self._entries[cmd] = {'pattern': cmd, 'risk': 1, 'description': 'varsayilan_guvenli', 'added_at': time.time()}
    @property
    def entry_count(self) -> int:
        return len(self._entries)
    @property
    def override_count(self) -> int:
        return len(self._overrides)
    def add(self, pattern: str = "", risk_level: int = 1, description: str = "") -> dict[str, Any]:
        try:
            if not pattern: return {'added': False, 'error': 'desen_gerekli'}
            risk = max(1, min(10, risk_level))
            self._entries[pattern] = {'pattern': pattern, 'risk': risk, 'description': description, 'added_at': time.time()}
            self._stats['added'] += 1
            self._log_action('add', pattern, {'risk': risk})
            return {'added': True, 'pattern': pattern, 'risk': risk}
        except Exception as e:
            return {'added': False, 'error': str(e)}
    def remove(self, pattern: str = "") -> dict[str, Any]:
        try:
            if not pattern: return {'removed': False, 'error': 'desen_gerekli'}
            if pattern not in self._entries: return {'removed': False, 'error': 'desen_bulunamadi', 'pattern': pattern}
            self._entries.pop(pattern)
            self._stats['removed'] += 1
            self._log_action('remove', pattern, {})
            return {'removed': True, 'pattern': pattern}
        except Exception as e:
            return {'removed': False, 'error': str(e)}
    def check(self, command: str = "") -> dict[str, Any]:
        try:
            if not command: return {'allowed': False, 'error': 'komut_gerekli'}
            self._stats['checks'] += 1
            cmd_base = command.split()[0] if command.split() else command
            for ov in self._overrides:
                if fnmatch.fnmatch(cmd_base, ov['pattern']):
                    allowed = ov.get('allowed', True)
                    self._stats['allowed' if allowed else 'denied'] += 1
                    return {'allowed': allowed, 'matched_override': ov['pattern'], 'command': command}
            for pattern, entry in self._entries.items():
                if fnmatch.fnmatch(cmd_base, pattern) or cmd_base == pattern:
                    self._stats['allowed'] += 1
                    return {'allowed': True, 'matched': pattern, 'risk': entry['risk'], 'command': command}
            self._stats['denied'] += 1
            self._log_action('deny', command, {})
            return {'allowed': False, 'reason': 'whitelist_disinda', 'command': command}
        except Exception as e:
            return {'allowed': False, 'error': str(e)}
    def score_risk(self, command: str = "") -> dict[str, Any]:
        try:
            if not command: return {'scored': False, 'error': 'komut_gerekli'}
            cmd_base = command.split()[0] if command.split() else command
            base_risk = 10
            for pattern, entry in self._entries.items():
                if fnmatch.fnmatch(cmd_base, pattern) or cmd_base == pattern:
                    base_risk = entry['risk']
                    break
            bonus = 0
            if "|" in command: bonus += 1
            if ">" in command or ">>" in command: bonus += 1
            if "&&" in command or ";" in command: bonus += 1
            if chr(36)+chr(40) in command: bonus += 2
            final_risk = min(10, base_risk + bonus)
            level = 'low' if final_risk <= 3 else 'medium' if final_risk <= 6 else 'high' if final_risk <= 8 else 'critical'
            return {'scored': True, 'command': command, 'risk': final_risk, 'level': level, 'base_risk': base_risk, 'bonus': bonus}
        except Exception as e:
            return {'scored': False, 'error': str(e)}
    def add_override(self, pattern: str = "", allowed: bool = True, reason: str = "") -> dict[str, Any]:
        try:
            if not pattern: return {'added': False, 'error': 'desen_gerekli'}
            self._overrides.append({'pattern': pattern, 'allowed': allowed, 'reason': reason, 'added_at': time.time()})
            return {'added': True, 'pattern': pattern, 'allowed': allowed}
        except Exception as e:
            return {'added': False, 'error': str(e)}
    def remove_override(self, pattern: str = "") -> dict[str, Any]:
        try:
            before = len(self._overrides)
            self._overrides = [ov for ov in self._overrides if ov['pattern'] != pattern]
            removed = len(self._overrides) < before
            return {'removed': removed, 'pattern': pattern}
        except Exception as e:
            return {'removed': False, 'error': str(e)}
    def get_all(self) -> dict[str, Any]:
        try:
            entries = [{'pattern': p, **e} for p, e in self._entries.items()]
            return {'retrieved': True, 'entries': entries, 'count': len(entries), 'overrides': self._overrides}
        except Exception as e:
            return {'retrieved': False, 'error': str(e)}
    def get_log(self, limit: int = 20) -> dict[str, Any]:
        try:
            recent = self._log[-limit:] if limit > 0 else list(self._log)
            return {'retrieved': True, 'log': recent, 'total': len(self._log), 'returned': len(recent)}
        except Exception as e:
            return {'retrieved': False, 'error': str(e)}
    def get_summary(self) -> dict[str, Any]:
        try:
            return {'retrieved': True, 'entry_count': self.entry_count, 'override_count': self.override_count, 'log_count': len(self._log), 'stats': dict(self._stats)}
        except Exception as e:
            return {'retrieved': False, 'error': str(e)}
    def _log_action(self, action: str, pattern: str, details: dict) -> None:
        self._log.append({'action': action, 'pattern': pattern, 'details': details, 'timestamp': time.time()})
