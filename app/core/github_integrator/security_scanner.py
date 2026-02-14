"""ATLAS Guvenlik Tarayici modulu.

Malware tespit, suphe li kod kaliplari,
izin analizi, ag erisim kontrolu ve sandbox gereksinimi.
"""

import logging
import re
from typing import Any

from app.models.github_integrator import (
    SecurityRisk,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)

# Supheli kod kaliplari
_SUSPICIOUS_PATTERNS: list[dict[str, Any]] = [
    {"pattern": r"os\.system\s*\(", "name": "os.system kullanimi", "risk": "high"},
    {"pattern": r"subprocess\.(?:call|run|Popen)\s*\(.*shell\s*=\s*True", "name": "shell=True subprocess", "risk": "high"},
    {"pattern": r"eval\s*\(", "name": "eval kullanimi", "risk": "critical"},
    {"pattern": r"exec\s*\(", "name": "exec kullanimi", "risk": "critical"},
    {"pattern": r"__import__\s*\(", "name": "dinamik import", "risk": "medium"},
    {"pattern": r"pickle\.loads?\s*\(", "name": "pickle deserializasyon", "risk": "high"},
    {"pattern": r"yaml\.(?:load|unsafe_load)\s*\(", "name": "guvenli olmayan YAML yukle", "risk": "high"},
    {"pattern": r"requests\.get\s*\(.*verify\s*=\s*False", "name": "SSL dogrulama kapali", "risk": "medium"},
    {"pattern": r"chmod\s+777", "name": "chmod 777 izin", "risk": "medium"},
    {"pattern": r"rm\s+-rf\s+/", "name": "tehlikeli rm -rf", "risk": "critical"},
    {"pattern": r"base64\.b64decode", "name": "base64 decode (gizli kod olabilir)", "risk": "low"},
    {"pattern": r"socket\.socket\s*\(", "name": "ham soket kullanimi", "risk": "medium"},
    {"pattern": r"ctypes\.", "name": "ctypes kullanimi", "risk": "medium"},
    {"pattern": r"keylog|keylogger|keystroke", "name": "tus kaydedici suplesi", "risk": "critical"},
    {"pattern": r"cryptocurrency|crypto\.miner|coinhive", "name": "kripto madencilik suplesi", "risk": "critical"},
]

# Ag erisim kaliplari
_NETWORK_PATTERNS: list[str] = [
    r"requests\.", r"urllib", r"httpx\.", r"aiohttp\.",
    r"socket\.", r"websocket", r"grpc\.",
    r"smtplib\.", r"ftplib\.", r"paramiko\.",
]

# Dosya sistemi erisim kaliplari
_FS_PATTERNS: list[str] = [
    r"open\s*\(", r"os\.(?:remove|unlink|rmdir|makedirs)",
    r"shutil\.(?:rmtree|move|copy)", r"pathlib\.Path",
    r"os\.walk", r"glob\.glob",
]

# Risk haritasi
_RISK_MAP: dict[str, SecurityRisk] = {
    "low": SecurityRisk.LOW,
    "medium": SecurityRisk.MEDIUM,
    "high": SecurityRisk.HIGH,
    "critical": SecurityRisk.CRITICAL,
}


class SecurityScanner:
    """Guvenlik tarama sistemi.

    Repo kodunu guvenlik acisindan tarar,
    supheli kaliplari tespit eder ve risk degerlendirir.

    Attributes:
        _scans: Tarama gecmisi.
    """

    def __init__(self) -> None:
        """Guvenlik tarayicisini baslatir."""
        self._scans: list[SecurityScanResult] = []
        logger.info("SecurityScanner baslatildi")

    def scan(
        self,
        repo_name: str,
        file_contents: dict[str, str],
    ) -> SecurityScanResult:
        """Guvenlik taramasi yapar.

        Args:
            repo_name: Repo adi.
            file_contents: Dosya icerikleri.

        Returns:
            SecurityScanResult nesnesi.
        """
        suspicious: list[str] = []
        findings: list[str] = []
        permissions: list[str] = []
        max_risk = SecurityRisk.SAFE

        # Supheli kalipler
        for path, content in file_contents.items():
            for pattern_info in _SUSPICIOUS_PATTERNS:
                if re.search(pattern_info["pattern"], content, re.IGNORECASE):
                    finding = f"{path}: {pattern_info['name']}"
                    suspicious.append(pattern_info["name"])
                    findings.append(finding)
                    risk = _RISK_MAP.get(pattern_info["risk"], SecurityRisk.LOW)
                    if self._risk_value(risk) > self._risk_value(max_risk):
                        max_risk = risk

        # Ag erisim kontrolu
        network_access = self._check_network_access(file_contents)
        if network_access:
            permissions.append("network_access")

        # Dosya sistemi erisim
        fs_access = self._check_fs_access(file_contents)
        if fs_access:
            permissions.append("file_system_access")

        # Malware kontrolu
        malware = self._check_malware(file_contents)

        # Sandbox gereksinimi
        requires_sandbox = (
            max_risk in (SecurityRisk.HIGH, SecurityRisk.CRITICAL)
            or malware
            or network_access
        )

        # Kurulum guvenli mi
        safe = (
            max_risk in (SecurityRisk.SAFE, SecurityRisk.LOW)
            and not malware
        )

        result = SecurityScanResult(
            repo_name=repo_name,
            risk_level=max_risk,
            malware_detected=malware,
            suspicious_patterns=suspicious,
            permissions_required=permissions,
            network_access=network_access,
            file_system_access=fs_access,
            requires_sandbox=requires_sandbox,
            safe_to_install=safe,
            findings=findings,
        )

        self._scans.append(result)
        return result

    def quick_scan(
        self, repo_name: str, content: str
    ) -> SecurityRisk:
        """Hizli risk degerlendirmesi yapar.

        Args:
            repo_name: Repo adi.
            content: Kod icerigi.

        Returns:
            SecurityRisk degeri.
        """
        max_risk = SecurityRisk.SAFE

        for pattern_info in _SUSPICIOUS_PATTERNS:
            if re.search(pattern_info["pattern"], content, re.IGNORECASE):
                risk = _RISK_MAP.get(pattern_info["risk"], SecurityRisk.LOW)
                if self._risk_value(risk) > self._risk_value(max_risk):
                    max_risk = risk

        return max_risk

    def is_safe_to_install(self, scan_result: SecurityScanResult) -> bool:
        """Kurulum guvenli mi kontrol eder.

        Args:
            scan_result: Tarama sonucu.

        Returns:
            Guvenli ise True.
        """
        return scan_result.safe_to_install

    def get_risk_summary(self) -> dict[str, Any]:
        """Risk ozetini getirir.

        Returns:
            Ozet sozlugu.
        """
        if not self._scans:
            return {"total_scans": 0}

        safe = sum(1 for s in self._scans if s.safe_to_install)
        risky = sum(1 for s in self._scans if not s.safe_to_install)
        malware = sum(1 for s in self._scans if s.malware_detected)

        return {
            "total_scans": len(self._scans),
            "safe_count": safe,
            "risky_count": risky,
            "malware_detected": malware,
        }

    def _check_network_access(self, contents: dict[str, str]) -> bool:
        """Ag erisimi kontrol eder."""
        all_content = " ".join(contents.values())
        return any(
            re.search(p, all_content) for p in _NETWORK_PATTERNS
        )

    def _check_fs_access(self, contents: dict[str, str]) -> bool:
        """Dosya sistemi erisimi kontrol eder."""
        all_content = " ".join(contents.values())
        return any(
            re.search(p, all_content) for p in _FS_PATTERNS
        )

    def _check_malware(self, contents: dict[str, str]) -> bool:
        """Malware kontrolu yapar."""
        all_content = " ".join(contents.values()).lower()

        malware_indicators = [
            "keylogger", "ransomware", "cryptominer",
            "reverse_shell", "backdoor", "trojan",
            "coinhive", "crypto.miner",
        ]

        return any(ind in all_content for ind in malware_indicators)

    def _risk_value(self, risk: SecurityRisk) -> int:
        """Risk degerini sayiya cevirir."""
        values = {
            SecurityRisk.SAFE: 0,
            SecurityRisk.LOW: 1,
            SecurityRisk.MEDIUM: 2,
            SecurityRisk.HIGH: 3,
            SecurityRisk.CRITICAL: 4,
        }
        return values.get(risk, 0)

    @property
    def scan_count(self) -> int:
        """Tarama sayisi."""
        return len(self._scans)
